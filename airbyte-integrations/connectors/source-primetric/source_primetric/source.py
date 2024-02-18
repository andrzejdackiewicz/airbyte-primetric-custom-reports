#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import json
from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import requests
from airbyte_cdk import AirbyteLogger
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream, HttpSubStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator
from airbyte_protocol.models import SyncMode


class PrimetricStream(HttpStream, ABC):
    url_base = "https://api.primetric.com/beta/"
    primary_key = "uuid"

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        next_page_url = response.json()["next"]
        return parse_qs(urlparse(next_page_url).query)

    def request_params(
            self,
            stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None,
    ) -> MutableMapping[str, Any]:
        return next_page_token

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        yield from response.json()["results"]

    def backoff_time(self, response: requests.Response) -> Optional[float]:
        """This method is called if we run into the rate limit.
        Rate Limits Docs: https://developer.primetric.com/#rate-limits"""
        return 31


class Assignments(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "assignments"


class Employees(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "employees"


class Hashtags(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "hash_tags"


class OrganizationClients(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "organization/clients"


class OrganizationCompanyGroups(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "organization/company_groups"


class OrganizationDepartments(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "organization/departments"


class OrganizationIdentityProviders(PrimetricStream):
    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None

    def parse_response(self, response: str, **kwargs) -> Iterable[Mapping]:
        yield from json.loads({"data": response.text})

    def path(self, **kwargs) -> str:
        return "organization/identity_providers"


class OrganizationPositions(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "organization/positions"


class OrganizationRagScopes(PrimetricStream):
    primary_key = "text"

    def path(self, **kwargs) -> str:
        return "organization/rag_scopes"


class OrganizationRoles(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "organization/roles"


class OrganizationSeniorities(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "organization/seniorities"


class OrganizationTags(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "organization/tags"


class OrganizationTeams(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "organization/teams"


class OrganizationTimeoffTypes(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "organization/timeoff_types"


class People(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "people"


class Projects(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "projects"


class ProjectsVacancies(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "projects_vacancies"


class RagRatings(PrimetricStream):
    primary_key = "project_id"

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None

    def parse_response(self, response: str, **kwargs) -> Iterable[Mapping]:
        yield from json.loads(response.text)

    def path(self, **kwargs) -> str:
        return "rag_ratings"


class Skills(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "skills"


class Timeoffs(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "timeoffs"


class Worklogs(PrimetricStream):
    @property
    def use_cache(self) -> bool:
        return True

    def path(self, **kwargs) -> str:
        return "worklogs"


class ReportsCustom(PrimetricStream):
    def path(self, **kwargs) -> str:
        return "reports/custom"


class ReportsCustomData(HttpSubStream, PrimetricStream):
    def __init__(self, parent, authenticator, **kwargs):
        super().__init__(parent=parent, authenticator=authenticator, **kwargs)

    def path(self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None,
             next_page_token: Mapping[str, Any] = None
             ) -> str:
        return f"reports/custom/{stream_slice['parent']['uuid']}/data"

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        yield from [{"uuid": ''.join(response.url.split("custom/")[1].split("/data")[0]), "data": response.text}]

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None

    def stream_slices(
            self,
            sync_mode: SyncMode = SyncMode.full_refresh,
            cursor_field: List[str] = None,
            stream_state: Mapping[str, Any] = None,
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        # gather parent stream records in full
        parent_stream_slices = self.parent.stream_slices(
            sync_mode=sync_mode, cursor_field=cursor_field, stream_state=stream_state
        )

        # iterate over parent stream slices
        for current_slice in parent_stream_slices:
            parent_records = self.parent.read_records(
                sync_mode=sync_mode, cursor_field=cursor_field, stream_slice=current_slice, stream_state=stream_state
            )

            for record in parent_records:
                yield {"parent": record}


class SourcePrimetric(AbstractSource):
    @staticmethod
    def get_connection_response(config: Mapping[str, Any]):
        token_refresh_endpoint = f'{"https://api.primetric.com/auth/token/"}'
        client_id = config["client_id"]
        client_secret = config["client_secret"]
        refresh_token = None
        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret,
                "refresh_token": refresh_token}

        try:
            response = requests.request(method="POST", url=token_refresh_endpoint, data=data, headers=headers)

        except Exception as e:
            raise Exception(f"Error while refreshing access token: {e}") from e

        return response

    def check_connection(self, logger: AirbyteLogger, config: Mapping[str, Any]) -> Tuple[bool, any]:
        try:

            if not config["client_secret"] or not config["client_id"]:
                raise Exception("Empty config values! Check your configuration file!")

            self.get_connection_response(config).raise_for_status()

            return True, None

        except Exception as e:
            return False, e

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        response = self.get_connection_response(config)
        response.raise_for_status()

        authenticator = TokenAuthenticator(response.json()["access_token"])
        reportsCustom = ReportsCustom(authenticator=authenticator)

        return [
            Assignments(authenticator=authenticator),
            Employees(authenticator=authenticator),
            Hashtags(authenticator=authenticator),
            OrganizationClients(authenticator=authenticator),
            OrganizationCompanyGroups(authenticator=authenticator),
            OrganizationDepartments(authenticator=authenticator),
            OrganizationIdentityProviders(authenticator=authenticator),
            OrganizationPositions(authenticator=authenticator),
            OrganizationRagScopes(authenticator=authenticator),
            OrganizationRoles(authenticator=authenticator),
            OrganizationSeniorities(authenticator=authenticator),
            OrganizationTags(authenticator=authenticator),
            OrganizationTeams(authenticator=authenticator),
            OrganizationTimeoffTypes(authenticator=authenticator),
            People(authenticator=authenticator),
            Projects(authenticator=authenticator),
            ProjectsVacancies(authenticator=authenticator),
            RagRatings(authenticator=authenticator),
            Skills(authenticator=authenticator),
            Timeoffs(authenticator=authenticator),
            Worklogs(authenticator=authenticator),
            reportsCustom,
            ReportsCustomData(parent=reportsCustom, authenticator=authenticator),
        ]
