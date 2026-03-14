"""CSV parser for SisReg schedule export (Arquivo Agendamento)."""

import csv
import io
import logging

from regulahub.sisreg.models import ScheduleExportRow

logger = logging.getLogger(__name__)

EXPORT_COLUMNS: list[str] = [
    "solicitacao",
    "codigo_interno",
    "codigo_unificado",
    "descricao_procedimento",
    "cpf_proficional_executante",
    "nome_profissional_executante",
    "data_agendamento",
    "hr_agendamento",
    "tipo",
    "cns",
    "nome",
    "dt_nascimento",
    "idade",
    "idade_meses",
    "nome_mae",
    "tipo_logradouro",
    "logradouro",
    "complemento",
    "numero_logradouro",
    "bairro",
    "cep",
    "telefone",
    "municipio",
    "ibge",
    "mun_solicitante",
    "ibge_solicitante",
    "cnes_solicitante",
    "unidade_fantasia",
    "sexo",
    "data_solicitacao",
    "operador_solicitante",
    "data_autorizacao",
    "operador_autorizador",
    "valor_procedimento",
    "situacao",
    "cid",
    "cpf_profissional_solicitante",
    "nome_profissional_solicitante",
]

EXPECTED_COLUMN_COUNT = len(EXPORT_COLUMNS)


def parse_export_csv(raw_bytes: bytes, encoding: str = "utf-8") -> list[ScheduleExportRow]:
    """Parse raw CSV bytes from SisReg schedule export into ScheduleExportRow list.

    - Delimiter: `;`
    - Skips header row
    - Skips malformed rows (< 38 columns) with warning
    - Strips whitespace from each field
    - Returns empty list if no data rows
    """
    text = raw_bytes.decode(encoding, errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=";")

    rows: list[ScheduleExportRow] = []
    for line_num, fields in enumerate(reader):
        if line_num == 0:
            # Skip header row
            continue

        if len(fields) < EXPECTED_COLUMN_COUNT:
            logger.warning(
                "Skipping malformed row %d: expected %d columns, got %d",
                line_num + 1,
                EXPECTED_COLUMN_COUNT,
                len(fields),
            )
            continue

        # Build dict from column names → stripped field values
        data = {col: fields[idx].strip() for idx, col in enumerate(EXPORT_COLUMNS)}
        rows.append(ScheduleExportRow(**data))

    return rows
