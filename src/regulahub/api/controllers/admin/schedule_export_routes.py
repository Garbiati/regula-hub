"""Admin routes for SisReg schedule export (Arquivo Agendamento)."""

import logging
import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from regulahub.api.controllers.admin.schemas import (
    CachedExportQueryRequest,
    CachedExportResponse,
    CadsusEnrichRequest,
    CadsusEnrichResponse,
    CadsusPatientEnrichment,
    EnrichedExportItemResponse,
    EnrichedExportListResponse,
    OperatorScheduleExportResponse,
    PersistExportRequest,
    PersistExportResponse,
    ScheduleExportItemResponse,
    ScheduleExportListResponse,
    ScheduleExportRequest,
)
from regulahub.api.deps import verify_api_key
from regulahub.api.rate_limit import limiter
from regulahub.db.engine import get_session
from regulahub.services.credential_service import CredentialNotFoundError, resolve_credential_by_username
from regulahub.services.schedule_export_service import (
    build_csv_bytes,
    build_txt_bytes,
    export_schedules,
    export_single_operator_resolved,
    get_cached_exports,
    persist_export_rows,
)
from regulahub.sisreg.client import SisregLoginError
from regulahub.sisreg.models import EnrichedExportRow, ExportFilters, ScheduleExportRow
from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/sisreg/schedule-export",
    tags=["admin-sisreg-export"],
    dependencies=[Depends(verify_api_key)],
)


def _to_export_filters(req: ScheduleExportRequest) -> ExportFilters:
    """Map request schema to domain ExportFilters."""
    return ExportFilters(
        date_from=req.date_from,
        date_to=req.date_to,
        profile_type=req.profile_type,
        usernames=req.usernames,
    )


def _filter_by_procedure(rows: list[ScheduleExportRow], procedure_filter: str | None) -> list[ScheduleExportRow]:
    """Filter rows by procedure description (case-insensitive contains)."""
    if not procedure_filter:
        return rows
    filter_lower = procedure_filter.lower()
    return [r for r in rows if filter_lower in r.descricao_procedimento.lower()]


def _map_row_to_response(row: ScheduleExportRow) -> ScheduleExportItemResponse:
    return ScheduleExportItemResponse(
        solicitacao=row.solicitacao,
        codigo_interno=row.codigo_interno,
        codigo_unificado=row.codigo_unificado,
        descricao_procedimento=row.descricao_procedimento,
        nome_profissional_executante=row.nome_profissional_executante,
        data_agendamento=row.data_agendamento,
        hr_agendamento=row.hr_agendamento,
        tipo=row.tipo,
        cns=row.cns,
        nome=row.nome,
        dt_nascimento=row.dt_nascimento,
        idade=row.idade,
        nome_mae=row.nome_mae,
        telefone=row.telefone,
        municipio=row.municipio,
        cnes_solicitante=row.cnes_solicitante,
        unidade_fantasia=row.unidade_fantasia,
        sexo=row.sexo,
        data_solicitacao=row.data_solicitacao,
        situacao=row.situacao,
        cid=row.cid,
        nome_profissional_solicitante=row.nome_profissional_solicitante,
    )


@router.post("/enrich", response_model=CadsusEnrichResponse)
@limiter.limit("30/minute")
async def enrich_with_cadsus_endpoint(
    request: Request,
    body: CadsusEnrichRequest,
    db_session: AsyncSession = Depends(get_session),
) -> CadsusEnrichResponse:
    """Enrich patients by CNS with transparent cache.

    Flow:
    1. Check enrichment cache for fresh entries (< 30 days)
    2. CADSUS lookup for pending CNS only
    3. SisReg CadWeb fallback for CADSUS failures
    4. Upsert new results to enrichment cache
    5. Return cached + fresh results transparently
    """
    import asyncio
    from datetime import UTC, datetime

    from regulahub.config import get_cadsus_settings
    from regulahub.db.repositories.enrichment_cache import EnrichmentCacheRepository
    from regulahub.integrations.cadsus_client import CadsusClient
    from regulahub.sisreg.client import SisregClient

    unique_cns = list(set(body.cns_list))
    results: dict[str, CadsusPatientEnrichment] = {}
    from_cache = 0

    # ── Phase 0: Enrichment cache lookup ──
    cache_repo = EnrichmentCacheRepository(db_session)
    cached = await cache_repo.find_fresh_by_cns_list(unique_cns)

    for cns, entry in cached.items():
        if entry.cpf:
            results[cns] = CadsusPatientEnrichment(
                cpf=entry.cpf,
                phone=entry.phone,
                email=entry.email,
                father_name=entry.father_name,
                race=entry.race,
                cns_definitivo=entry.cns_definitivo,
            )
            from_cache += 1

    pending_cns = [cns for cns in unique_cns if cns not in results]
    logger.info("Enrichment cache: %d cached, %d pending CADSUS lookup", from_cache, len(pending_cns))

    # ── Phase 1: CADSUS (batch, fast) — only pending CNS ──
    failed_cns: list[str] = []
    new_results_source: dict[str, str] = {}  # cns → "CADSUS" or "CADWEB"

    settings = get_cadsus_settings()
    if pending_cns and settings.cadsus_enabled:
        cadsus = CadsusClient(settings=settings)
        semaphore = asyncio.Semaphore(40)

        async def _cadsus_lookup(cns: str) -> bool:
            async with semaphore:
                patient = await cadsus.get_patient_by_cns(cns)
                if patient is None:
                    return False
                if patient.cpf:
                    phone = _extract_mobile(patient.phone)
                    results[cns] = CadsusPatientEnrichment(cpf=patient.cpf, phone=phone)
                    new_results_source[cns] = "CADSUS"
                return True

        logger.info("Enrichment phase 1 (CADSUS): %d pending CNS", len(pending_cns))
        outcomes = await asyncio.gather(*[_cadsus_lookup(cns) for cns in pending_cns])
        failed_cns = [cns for cns, ok in zip(pending_cns, outcomes, strict=True) if not ok and cns not in results]
        logger.info("CADSUS: %d resolved, %d failed", len(pending_cns) - len(failed_cns), len(failed_cns))
    elif pending_cns:
        failed_cns = pending_cns

    # ── Phase 2: SisReg CadWeb fallback (serial, rate-limited) ──
    fallback_found = 0
    if failed_cns and body.sisreg_username and body.sisreg_profile_type:
        try:
            resolved_username, password = await resolve_credential_by_username(
                system="SISREG",
                profile_type=body.sisreg_profile_type,
                username=body.sisreg_username,
                db_session=db_session,
            )
            user_hash = mask_username(resolved_username)
            logger.info("Enrichment phase 2 (SisReg CadWeb): %d CNS via %s", len(failed_cns), user_hash)

            sisreg_semaphore = asyncio.Semaphore(2)

            async def _cadweb_lookup(client: SisregClient, cns: str) -> None:
                nonlocal fallback_found
                async with sisreg_semaphore:
                    patient = await client.cadweb_lookup(cns)
                    if patient and patient.cpf:
                        phone = _format_cadweb_phone(patient.phone_type, patient.phone_ddd, patient.phone_number)
                        results[cns] = CadsusPatientEnrichment(cpf=patient.cpf, phone=phone)
                        new_results_source[cns] = "CADWEB"
                        fallback_found += 1

            base_url = "https://sisregiii.saude.gov.br"
            async with SisregClient(base_url, resolved_username, password, body.sisreg_profile_type) as client:
                await asyncio.gather(*[_cadweb_lookup(client, cns) for cns in failed_cns])

            logger.info("SisReg CadWeb fallback: %d/%d resolved", fallback_found, len(failed_cns))
        except Exception:
            logger.exception("SisReg CadWeb fallback failed")

    # Apply phone fallback — for patients with CPF but no phone, try export CSV phone
    for cns, enrichment in results.items():
        if not enrichment.phone and cns in body.phone_fallbacks:
            enrichment.phone = _extract_mobile(body.phone_fallbacks[cns])

    # ── Phase 3: Persist new results to enrichment cache ──
    if new_results_source:
        now = datetime.now(UTC)
        cache_entries = [
            {
                "cns": cns,
                "cpf": results[cns].cpf,
                "phone": results[cns].phone,
                "email": results[cns].email,
                "father_name": results[cns].father_name,
                "race": results[cns].race,
                "cns_definitivo": results[cns].cns_definitivo,
                "source": source,
                "enriched_at": now,
            }
            for cns, source in new_results_source.items()
            if cns in results
        ]
        try:
            persisted = await cache_repo.bulk_upsert(cache_entries)
            await db_session.commit()
            logger.info("Enrichment cache: %d new entries persisted", persisted)
        except Exception:
            await db_session.rollback()
            logger.exception("Failed to persist enrichment cache (non-fatal)")

    final_failed = len(unique_cns) - len(results)
    return CadsusEnrichResponse(
        results=results,
        total=len(unique_cns),
        found=len(results),
        failed=final_failed,
        fallback_found=fallback_found,
        from_cache=from_cache,
    )


def _extract_mobile(phone: str | None) -> str | None:
    """Extract the best mobile phone from a raw phone string.

    Brazilian mobile: DDD (2 digits) + 9 + 8 digits.
    Handles multiple phones separated by / ; ,
    Input examples: "(92)99138-4577", "92 991384577", "(92)99138-4577/(92)3234-5678"
    """
    if not phone:
        return None
    # Split on common separators to handle multiple phones
    for part in re.split(r"[/;,]+", phone):
        digits = re.sub(r"\D", "", part)
        # 11 digits: DDD(2) + 9 + number(8)
        if len(digits) == 11 and digits[2] == "9":
            return f"({digits[:2]}){digits[2:7]}-{digits[7:]}"
    return None


def _format_cadweb_phone(phone_type: str | None, ddd: str | None, number: str | None) -> str | None:
    """Format CadWeb phone as a single mobile number. Returns None if not CELULAR."""
    if not phone_type or not ddd or not number:
        return None
    if phone_type.upper() != "CELULAR":
        return None
    clean_ddd = re.sub(r"\D", "", ddd)
    clean_number = re.sub(r"\D", "", number)
    if clean_ddd and clean_number:
        return f"({clean_ddd}){clean_number}"
    return None


@router.post("/operator", response_model=OperatorScheduleExportResponse)
@limiter.limit("30/minute")
async def export_single_operator_endpoint(
    request: Request,
    body: ScheduleExportRequest,
    db_session: AsyncSession = Depends(get_session),
) -> OperatorScheduleExportResponse:
    """Export schedule data for exactly one operator.

    Used by the pipeline visualization to track per-operator progress.
    """
    if len(body.usernames) != 1:
        raise HTTPException(status_code=422, detail="Exactly one username is required for single-operator export")

    username = body.usernames[0]
    try:
        resolved_username, password = await resolve_credential_by_username(
            system="SISREG",
            profile_type=body.profile_type,
            username=username,
            db_session=db_session,
        )
    except CredentialNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    user_hash = mask_username(resolved_username)
    try:
        rows = await export_single_operator_resolved(
            resolved_username, password, body.profile_type, body.date_from, body.date_to,
        )
        filtered = _filter_by_procedure(rows, body.procedure_filter)
        items = [_map_row_to_response(row) for row in filtered]
        logger.info("Single-operator export: %s returned %d items", user_hash, len(items))
        return OperatorScheduleExportResponse(operator=username, items=items, total=len(items))
    except SisregLoginError:
        logger.error("SisReg login failed for export user %s", user_hash)
        raise HTTPException(status_code=502, detail="SisReg login failed") from None
    except Exception:
        logger.exception("SisReg export error for user %s", user_hash)
        raise HTTPException(status_code=502, detail="SisReg export failed") from None


@router.post("", response_model=ScheduleExportListResponse | EnrichedExportListResponse)
@limiter.limit("5/minute")
async def schedule_export_json(
    request: Request,
    body: ScheduleExportRequest,
    db_session: AsyncSession = Depends(get_session),
):
    """Export schedule data as JSON."""
    try:
        filters = _to_export_filters(body)
        result = await export_schedules(filters, db_session)
    except CredentialNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SisregLoginError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    total_unfiltered = result.total
    filtered_rows = _filter_by_procedure(result.items, body.procedure_filter)

    if body.enrich:
        try:
            from regulahub.services.schedule_export_service import enrich_rows_with_cadsus

            enriched = await enrich_rows_with_cadsus(filtered_rows, body.procedure_filter)
            enriched_items = [
                EnrichedExportItemResponse(
                    **_map_row_to_response(row).model_dump(),
                    cpf_paciente=row.cpf_paciente if hasattr(row, "cpf_paciente") else None,
                    email_paciente=row.email_paciente if hasattr(row, "email_paciente") else None,
                    telefone_cadsus=row.telefone_cadsus if hasattr(row, "telefone_cadsus") else None,
                    nome_pai=row.nome_pai if hasattr(row, "nome_pai") else None,
                    raca=row.raca if hasattr(row, "raca") else None,
                    cns_definitivo=row.cns_definitivo if hasattr(row, "cns_definitivo") else None,
                )
                for row in enriched
            ]
            enriched_count = sum(1 for r in enriched_items if r.cpf_paciente)
            return EnrichedExportListResponse(
                items=enriched_items,
                total=len(enriched_items),
                total_unfiltered=total_unfiltered,
                operators_queried=result.operators_queried,
                operators_succeeded=result.operators_succeeded,
                enriched_count=enriched_count,
                procedure_filter=body.procedure_filter,
            )
        except ImportError:
            logger.warning("CADSUS enrichment not available, returning unenriched results")

    items = [_map_row_to_response(row) for row in filtered_rows]
    return ScheduleExportListResponse(
        items=items,
        total=len(items),
        operators_queried=result.operators_queried,
        operators_succeeded=result.operators_succeeded,
    )


@router.post("/csv")
@limiter.limit("3/minute")
async def schedule_export_csv(
    request: Request,
    body: ScheduleExportRequest,
    db_session: AsyncSession = Depends(get_session),
):
    """Export schedule data as CSV file download."""
    try:
        filters = _to_export_filters(body)
        result = await export_schedules(filters, db_session)
    except CredentialNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SisregLoginError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    filtered_rows = _filter_by_procedure(result.items, body.procedure_filter)
    csv_bytes = build_csv_bytes(filtered_rows)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")

    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="schedule_export_{timestamp}.csv"'},
    )


@router.post("/txt")
@limiter.limit("3/minute")
async def schedule_export_txt(
    request: Request,
    body: ScheduleExportRequest,
    db_session: AsyncSession = Depends(get_session),
):
    """Export schedule data as TXT file download (tab-separated)."""
    try:
        filters = _to_export_filters(body)
        result = await export_schedules(filters, db_session)
    except CredentialNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SisregLoginError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    filtered_rows = _filter_by_procedure(result.items, body.procedure_filter)
    txt_bytes = build_txt_bytes(filtered_rows)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")

    return StreamingResponse(
        iter([txt_bytes]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="schedule_export_{timestamp}.txt"'},
    )


@router.post("/cached", response_model=CachedExportResponse)
@limiter.limit("30/minute")
async def query_cached_exports(
    request: Request,
    body: CachedExportQueryRequest,
    db_session: AsyncSession = Depends(get_session),
) -> CachedExportResponse:
    """Query cached schedule export rows from database.

    Returns EnrichedExportItemResponse so enrichment fields (cpf_paciente, etc.)
    from previous runs are preserved and sent to the frontend.
    """
    rows = await get_cached_exports(body.date_from, body.date_to, body.procedure_filter, db_session)
    items: list[EnrichedExportItemResponse] = []
    for row in rows:
        base = _map_row_to_response(row)
        if isinstance(row, EnrichedExportRow):
            items.append(EnrichedExportItemResponse(
                **base.model_dump(),
                cpf_paciente=row.cpf_paciente,
                email_paciente=row.email_paciente,
                telefone_cadsus=row.telefone_cadsus,
                nome_pai=row.nome_pai,
                raca=row.raca,
                cns_definitivo=row.cns_definitivo,
            ))
        else:
            items.append(EnrichedExportItemResponse(**base.model_dump()))
    logger.info("Cached export query: %d rows returned", len(items))
    return CachedExportResponse(items=items, total=len(items))


@router.post("/persist", response_model=PersistExportResponse)
@limiter.limit("10/minute")
async def persist_export_rows_endpoint(
    request: Request,
    body: PersistExportRequest,
    db_session: AsyncSession = Depends(get_session),
) -> PersistExportResponse:
    """Persist schedule export rows (with optional enrichment data) to database cache via upsert."""
    from regulahub.sisreg.models import EnrichedExportRow

    domain_rows = [
        EnrichedExportRow(
            solicitacao=item.solicitacao,
            codigo_interno=item.codigo_interno,
            codigo_unificado=item.codigo_unificado,
            descricao_procedimento=item.descricao_procedimento,
            nome_profissional_executante=item.nome_profissional_executante,
            data_agendamento=item.data_agendamento,
            hr_agendamento=item.hr_agendamento,
            tipo=item.tipo,
            cns=item.cns,
            nome=item.nome,
            dt_nascimento=item.dt_nascimento,
            idade=item.idade,
            nome_mae=item.nome_mae,
            telefone=item.telefone,
            municipio=item.municipio,
            cnes_solicitante=item.cnes_solicitante,
            unidade_fantasia=item.unidade_fantasia,
            sexo=item.sexo,
            data_solicitacao=item.data_solicitacao,
            situacao=item.situacao,
            cid=item.cid,
            nome_profissional_solicitante=item.nome_profissional_solicitante,
            cpf_paciente=item.cpf_paciente,
            email_paciente=item.email_paciente,
            telefone_cadsus=item.telefone_cadsus,
            nome_pai=item.nome_pai,
            raca=item.raca,
            cns_definitivo=item.cns_definitivo,
        )
        for item in body.items
        if item.solicitacao
    ]
    count = await persist_export_rows(domain_rows, db_session)
    logger.info("Persist export: %d rows upserted", count)
    return PersistExportResponse(persisted=count)
