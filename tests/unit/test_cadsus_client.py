"""Tests for CADSUS client integration."""

import httpx
import pytest
import respx

from regulahub.config import CadsusSettings
from regulahub.integrations.cadsus_client import (
    CNS_CODE,
    CPF_CODE,
    CadsusClient,
)

AUTH_URL = "https://ehr-auth.saude.gov.br"
SERVICES_URL = "https://servicos.saude.gov.br"

TOKEN_RESPONSE = {"access_token": "test-jwt-token", "expires_in": 3600}

SOAP_RESPONSE_FOUND = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:urn="urn:hl7-org:v3">
<soap:Body>
<urn:PRPA_IN201306UV02>
  <urn:controlActProcess>
    <urn:queryAck>
      <urn:queryResponseCode code="OK"/>
      <urn:resultTotalQuantity value="1"/>
    </urn:queryAck>
    <urn:subject>
      <urn:registrationEvent>
        <urn:subject1>
          <urn:patient>
            <urn:patientPerson>
              <urn:name>
                <urn:given>MARIA SILVA SANTOS</urn:given>
              </urn:name>
              <urn:telecom use="ORN" value="92991234567"/>
              <urn:telecom use="NET" value="maria@email.com"/>
              <urn:administrativeGenderCode code="F"/>
              <urn:birthTime value="19900115"/>
              <urn:addr>
                <urn:streetName>RUA DAS FLORES</urn:streetName>
                <urn:houseNumber>123</urn:houseNumber>
                <urn:additionalLocator>CENTRO</urn:additionalLocator>
                <urn:city>MANAUS</urn:city>
                <urn:postalCode>69000100</urn:postalCode>
                <urn:country>BR</urn:country>
              </urn:addr>
              <urn:raceCode code="03"/>
              <urn:personalRelationship>
                <urn:code code="PRN"/>
                <urn:relationshipHolder1>
                  <urn:name><urn:given>ANA SILVA</urn:given></urn:name>
                </urn:relationshipHolder1>
              </urn:personalRelationship>
              <urn:personalRelationship>
                <urn:code code="NPRN"/>
                <urn:relationshipHolder1>
                  <urn:name><urn:given>JOSE SANTOS</urn:given></urn:name>
                </urn:relationshipHolder1>
              </urn:personalRelationship>
              <urn:asOtherIDs>
                <urn:id root="2.16.840.1.113883.13.237" extension="12345678901"/>
              </urn:asOtherIDs>
              <urn:asOtherIDs>
                <urn:id root="2.16.840.1.113883.13.236" extension="898006209973606"/>
                <urn:id root="2.16.840.1.113883.13.236.1" extension="D"/>
              </urn:asOtherIDs>
              <urn:asOtherIDs>
                <urn:id root="2.16.840.1.113883.13.236" extension="700108994637420"/>
                <urn:id root="2.16.840.1.113883.13.236.1" extension="P"/>
              </urn:asOtherIDs>
            </urn:patientPerson>
            <urn:subjectOf1>
              <urn:queryMatchObservation>
                <urn:value value="100"/>
              </urn:queryMatchObservation>
            </urn:subjectOf1>
          </urn:patient>
        </urn:subject1>
      </urn:registrationEvent>
    </urn:subject>
  </urn:controlActProcess>
</urn:PRPA_IN201306UV02>
</soap:Body>
</soap:Envelope>"""

SOAP_RESPONSE_NOT_FOUND = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:urn="urn:hl7-org:v3">
<soap:Body>
<urn:PRPA_IN201306UV02>
  <urn:controlActProcess>
    <urn:queryAck>
      <urn:queryResponseCode code="NF"/>
      <urn:resultTotalQuantity value="0"/>
    </urn:queryAck>
  </urn:controlActProcess>
</urn:PRPA_IN201306UV02>
</soap:Body>
</soap:Envelope>"""


def _settings():
    return CadsusSettings(
        cadsus_auth_url=AUTH_URL,
        cadsus_services_url=SERVICES_URL,
        cadsus_enabled=True,
        cadsus_token_margin_seconds=0,
    )


class TestCadsusClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_patient_found(self):
        respx.get(f"{AUTH_URL}/api/osb/token").mock(return_value=httpx.Response(200, json=TOKEN_RESPONSE))
        respx.post(f"{SERVICES_URL}/cadsus/v2/PDQSupplierJWT").mock(
            return_value=httpx.Response(200, text=SOAP_RESPONSE_FOUND)
        )

        client = CadsusClient(settings=_settings())
        result = await client.get_patient_by_cns("898006209973606")

        assert result is not None
        assert result.cpf == "12345678901"
        assert result.first_name == "MARIA"
        assert result.last_name == "SILVA SANTOS"
        assert result.email == "maria@email.com"
        assert result.phone == "92991234567"
        assert result.gender == "F"
        assert result.birth_date == "15/01/1990"
        assert result.mother_name == "ANA SILVA"
        assert result.father_name == "JOSE SANTOS"
        assert result.race == "03"
        assert result.cns == "898006209973606"  # Definitive CNS preferred
        assert result.match_score == 100
        assert result.address is not None
        assert result.address.logradouro == "RUA DAS FLORES"
        assert result.address.numero == "123"
        assert result.address.bairro == "CENTRO"
        assert result.address.cidade == "MANAUS"
        assert result.address.cep == "69000100"

    @respx.mock
    @pytest.mark.asyncio
    async def test_patient_not_found(self):
        respx.get(f"{AUTH_URL}/api/osb/token").mock(return_value=httpx.Response(200, json=TOKEN_RESPONSE))
        respx.post(f"{SERVICES_URL}/cadsus/v2/PDQSupplierJWT").mock(
            return_value=httpx.Response(200, text=SOAP_RESPONSE_NOT_FOUND)
        )

        client = CadsusClient(settings=_settings())
        result = await client.get_patient_by_cns("999999999999999")

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_token_cached(self):
        token_route = respx.get(f"{AUTH_URL}/api/osb/token").mock(return_value=httpx.Response(200, json=TOKEN_RESPONSE))
        respx.post(f"{SERVICES_URL}/cadsus/v2/PDQSupplierJWT").mock(
            return_value=httpx.Response(200, text=SOAP_RESPONSE_FOUND)
        )

        client = CadsusClient(settings=_settings())
        await client.get_patient_by_cns("111")
        await client.get_patient_by_cns("222")

        # Token should only be fetched once
        assert token_route.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_connection_failure_returns_none(self):
        respx.get(f"{AUTH_URL}/api/osb/token").mock(return_value=httpx.Response(200, json=TOKEN_RESPONSE))
        respx.post(f"{SERVICES_URL}/cadsus/v2/PDQSupplierJWT").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        client = CadsusClient(settings=_settings())
        result = await client.get_patient_by_cns("111222333444555")

        assert result is None

    @pytest.mark.asyncio
    async def test_disabled_returns_none(self):
        settings = CadsusSettings(
            cadsus_auth_url=AUTH_URL,
            cadsus_services_url=SERVICES_URL,
            cadsus_enabled=False,
        )
        client = CadsusClient(settings=settings)
        result = await client.get_patient_by_cns("111222333444555")
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_soap_request_contains_cns(self):
        respx.get(f"{AUTH_URL}/api/osb/token").mock(return_value=httpx.Response(200, json=TOKEN_RESPONSE))
        soap_route = respx.post(f"{SERVICES_URL}/cadsus/v2/PDQSupplierJWT").mock(
            return_value=httpx.Response(200, text=SOAP_RESPONSE_FOUND)
        )

        client = CadsusClient(settings=_settings())
        await client.get_patient_by_cns("898006209973606")

        req_body = soap_route.calls.last.request.content.decode()
        assert "898006209973606" in req_body
        assert CNS_CODE in req_body

    def test_build_soap_request_structure(self):
        client = CadsusClient(settings=_settings())
        xml = client._build_soap_request("123456789012345", is_cpf=False)
        assert "PRPA_IN201305UV02" in xml
        assert "livingSubjectId" in xml
        assert CNS_CODE in xml
        assert "123456789012345" in xml

    def test_build_soap_request_cpf(self):
        client = CadsusClient(settings=_settings())
        xml = client._build_soap_request("12345678901", is_cpf=True)
        assert CPF_CODE in xml

    def test_parse_not_found_response(self):
        client = CadsusClient(settings=_settings())
        result = client._parse_soap_response(SOAP_RESPONSE_NOT_FOUND)
        assert result is None

    def test_parse_found_response(self):
        client = CadsusClient(settings=_settings())
        result = client._parse_soap_response(SOAP_RESPONSE_FOUND)
        assert result is not None
        assert result.cpf == "12345678901"
        assert result.mother_name == "ANA SILVA"
        assert result.father_name == "JOSE SANTOS"
