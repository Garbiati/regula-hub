"""add department_address column to integration_departments

Revision ID: 007
Revises: 006
Create Date: 2026-03-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADDRESSES = {
    "197130": "Aplicativo Saúde AM Digital",
    "2017210": "Avenida Tancredo Neves, s/nº, Parque 10, Manaus/AM",
    "2011824": "Av. Brasil, SN - Compensa, Manaus - AM",
    "2018527": "Av. Cosme Ferreira, s/n - São José, Manaus - AM",
    "2018519": "RUA FELISMINO SOARES, 213 - COL OLIVEIRA MACHADO",
    "2016982": "Av. Cristã, 690 - Colônia Terra Nova, Manaus - AM",
    "2013738": "AUTAZ MIRIM, 950 - JORGE TEIXEIRA",
    "2013592": "Av. Samaúma, 606 - Monte das Oliveiras",
    "2011840": "Rua Prof. Abílio Alencar, 367 - Alvorada II",
    "3212270": "AVENIDA BRASIL, SN - COMPENSA II",
    "2012057": "AV DES. FELISMINO SOARES, 115 - COL.OLIVEIRA MACHADO",
    "5889545": "RUA TERESINA, 99 - NOSSA SENHORA DAS GRAÇAS",
    "5726832": "Interior",
    "2013606": "PEDRO TEIXEIRA, SN - D PEDRO I",
    "2018756": "Av. Codajás, 26 - Cachoeirinha, Manaus - AM",
    "7778651": "AV JOAQUIM NABUCO, 1359 - CENTRO",
    "3500179": "Av. Margarita, s/n - Nova Cidade, Manaus - AM",
    "3042626": "Av. Autaz Mirim, 7035 - Tancredo Neves, Manaus - AM",
    "5222710": "R. Maracanã, 13 - Redenção, Manaus - AM",
    "2704951": "AVENIDA MARIO YPIRANGA, 1999 - ADRIANOPOLIS",
    "2014750": "RUA A, SN - CONJ. RIBEIRO JUNIOR",
    "2013479": "AVENIDA PRESIDENTE DUTRA, SN - GLORIA",
    "2013916": "AVENIDA COSME FERREIRA, SN - ZUMBI DOS PALMARES",
    "7594372": "RUA RIO MAICURU, SN - LAGO AZUL",
    "2013878": "RUA 7 DE SETEMBRO, SN - JORGE TEIXEIRA",
    "2013002": "TRAVESSA COMANDANTE FERRAZ, 15 - BETANIA",
    "2013517": "RUA LEOPOLDO NEVES, SN, SANTA LUZIA",
    "2014769": "RUA SAO TOME, SN - SAO RAIMUNDO",
}


def upgrade() -> None:
    op.add_column("integration_departments", sa.Column("department_address", sa.String(500), nullable=True))

    for cnes, address in ADDRESSES.items():
        op.execute(
            sa.text(
                "UPDATE integration_departments SET department_address = :addr WHERE cnes_code = :cnes"
            ).bindparams(addr=address, cnes=cnes)
        )


def downgrade() -> None:
    op.drop_column("integration_departments", "department_address")
