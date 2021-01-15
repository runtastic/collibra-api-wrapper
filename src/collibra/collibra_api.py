from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode
import requests
import pprint
import os

class Collibra:
    def __init__(self, base_url, user, password):
        self.base_url = base_url
        self.user_name = user
        self.password = password
        self.headers = {"Content-Type": "application/json"}
        self.connection_params = {
              "headers": self.headers,
              "auth": HTTPBasicAuth(self.user_name, self.password)}
        self.query_limit = 3000

    def __check_status_code(self, status_code, expected_status_code=200):
        """
        Compare the obtained status code with the expected value and raise an error if they don't match.

        Keyword arguments:
        status_code -- the code returned by the request
        expected_status_code -- the expected return code if everything went well (default 200)
        """
        if status_code != expected_status_code:
            raise RuntimeError(f"Request returned status {status_code}, {expected_status_code} expected.")

    def __check_get_request(self, r):
        self.__check_status_code(r.status_code)
        if r.json()["total"] == 0:
            object_id = None
        else:
            object_id = r.json()["results"][0]["id"]
        return object_id

    def get_community_id(self, community_name, nameMatchMode="EXACT", parentId=None):
        query_dict = {
            "nameMatchMode" : nameMatchMode
            , "name" : community_name
        }
        if parentId is not None:
            query_dict.update({"parentId" : parentId})
        query_string = urlencode(query_dict)
        r = requests.get(f'{self.base_url}/communities?{query_string}', **self.connection_params)
        return self.__check_get_request(r)

    def get_domain_id(self, domain_name, nameMatchMode="EXACT", communityId=None):
        query_dict = {
            "nameMatchMode" : nameMatchMode
            , "name" : domain_name
        }
        if communityId is not None:
            query_dict.update({"communityId" : communityId})
        query_string = urlencode(query_dict)
        r = requests.get(f'{self.base_url}/domains?{query_string}', **self.connection_params)
        return self.__check_get_request(r)


    def get_available_asset_types(self):
        r = requests.get(f'{self.base_url}/assetTypes', **self.connection_params)
        return [d['name'] for d in r.json()['results']]

    def get_asset_type_id(self, assetType_name, nameMatchMode="EXACT"):
        query_dict = {
            "nameMatchMode": nameMatchMode,
            "name": assetType_name
        }
        query_string = urlencode(query_dict)
        r = requests.get(f'{self.base_url}/assetTypes?{query_string}', **self.connection_params)
        return self.__check_get_request(r)

    def get_asset_id(self, asset_name, nameMatchMode="EXACT", domainId=None):
        query_dict = {
            "nameMatchMode": nameMatchMode,
            "name": asset_name
        }
        if domainId is not None:
            query_dict.update({"domainId": domainId})
        query_string = urlencode(query_dict)
        r = requests.get(f'{self.base_url}/assets?{query_string}', **self.connection_params)
        return self.__check_get_request(r)

    def get_assets(self, domainID):
        query_dict = {
            "domainId": domainID,
            "limit": self.query_limit
        }
        query_string = urlencode(query_dict)
        r = requests.get(f'{self.base_url}/assets?{query_string}', **self.connection_params)
        self.__check_status_code(r.status_code)
        return r.json()['results']

    def create_asset(self, asset_json):
        """
        Create an asset on Collibra

        Keyword arguments:
        asset_json -- json containing the asset details
        """
        r = requests.post(f'{self.base_url}/assets', json=asset_json, **self.connection_params)
        self.__check_status_code(r.status_code, 201)

    def create_assets(self, list_asset_json):
        """
        Create multiple assets by one single post (bulk option)

        Keyword arguments:
        asset_json -- list of json objects containing the asset details
        """
        r = requests.post(f'{self.base_url}/assets/bulk', json=list_asset_json, **self.connection_params)
        self.__check_status_code(r.status_code, 201)
        return {d['name']: d['id'] for d in r.json()}


    def get_available_attribute_types(self):
        r = requests.get(f'{self.base_url}/attributeTypes', **self.connection_params)
        return [d['name'] for d in r.json()['results']]

    def get_attribute_type_id(self, attributeType_name, nameMatchMode="EXACT"):
        query_dict = {
            "nameMatchMode" : nameMatchMode,
            "name" : attributeType_name
        }
        query_string = urlencode(query_dict)
        r = requests.get(f'{self.base_url}/attributeTypes?{query_string}', **self.connection_params)
        return self.__check_get_request(r)

    def get_attribute_id(self, typeIds, assetId):
        """
        Get id of an attribute inside an asset
        """
        query_dict = {
             "assetId" : assetId,
             "typeIds" : typeIds
        }
        query_string = urlencode(query_dict)
        r = requests.get(f'{self.base_url}/attributes?{query_string}', **self.connection_params)
        self.__check_status_code(r.status_code)
        return self.__check_get_request(r)

    def get_attributes(self, assetId):
        query_dict = {
            "assetId": assetId
        }
        query_string = urlencode(query_dict)
        r = requests.get(f'{self.base_url}/attributes?{query_string}', **self.connection_params)
        self.__check_status_code(r.status_code)
        return r.json()['results']

    def create_attribute(self, attribute_json):
        r = requests.post(f'{self.base_url}/attributes', json=attribute_json, **self.connection_params)
        self.__check_status_code(r.status_code, 201)

    def create_attributes(self, list_attribute_json):
        r = requests.post(f'{self.base_url}/attributes/bulk', json=list_attribute_json, **self.connection_params)
        self.__check_status_code(r.status_code, 201)

    def update_attribute(self, assetId, attribute_json):
        r = requests.patch(f'{self.base_url}/attributes/{assetId}', json=attribute_json, **self.connection_params)
        self.__check_status_code(r.status_code)

    def update_attributes(self, list_attribute_json):
        r = requests.patch(f'{self.base_url}/attributes/bulk', json=list_attribute_json, **self.connection_params)
        self.__check_status_code(r.status_code)

    def get_available_relation_types(self, asset_filter=None):
        r = requests.get(f'{self.base_url}/relationTypes', **self.connection_params)
        if asset_filter is None:
            res = [[d['sourceType']['name'],d['role'],d['coRole'],d['targetType']['name'],d['id']]
                    for d in r.json()['results'] if 'coRole' in d.keys()]
        elif len(asset_filter) == 1:
            res = [[d['sourceType']['name'], d['role'], d['coRole'], d['targetType']['name'],d['id']]
                    for d in r.json()['results'] if 'coRole' in d.keys() and
                   (asset_filter[0] == d['sourceType']['name'] or asset_filter[0] == d['targetType']['name'])]
        elif len(asset_filter) == 2:
            res = [[d['sourceType']['name'], d['role'], d['coRole'], d['targetType']['name'],d['id']]
                    for d in r.json()['results'] if 'coRole' in d.keys() and asset_filter[0] == d['sourceType']['name']
                    and asset_filter[1] == d['targetType']['name']]
        elif len(asset_filter) == 3:
            res = [[d['sourceType']['name'], d['role'], d['coRole'], d['targetType']['name'], d['id']]
                   for d in r.json()['results'] if 'coRole' in d.keys() and asset_filter[0] == d['sourceType']['name']
                   and asset_filter[1] == d['role'] and asset_filter[2] == d['targetType']['name']]
        else:
            res = None
        return res

    def create_relation_type(self, relation_json):
        r = requests.post(f'{self.base_url}relationTypes', json=relation_json, **self.connection_params)
        self.__check_status_code(r.status_code, 201)

    def create_relation(self, relation_json):
        r = requests.post(f'{self.base_url}/relations', json=relation_json, **self.connection_params)
        self.__check_status_code(r.status_code, 201)

    def create_relations(self, list_attribute_json):
        r = requests.post(f'{self.base_url}/relations/bulk', json=list_attribute_json, **self.connection_params)
        self.__check_status_code(r.status_code, 201)

    def get_relation_ids(self, query_dict):
        """
        Returns a list of relations matching the request
        """
        query_dict['limit'] = self.query_limit
        query_string = urlencode(query_dict)
        r = requests.get(f'{self.base_url}/relations?{query_string}', **self.connection_params)
        self.__check_status_code(r.status_code)
        return {'{}/{}'.format(d['source']['id'],d['target']['id']): d['id'] for d in r.json()['results']}

    def delete_relation(self, query_dict):
        query_string = urlencode(query_dict)
        r = requests.delete(f'{self.base_url}/relations?{query_string}', **self.connection_params)
        self.__check_status_code(r.status_code, 204)
