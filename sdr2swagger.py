#!/usr/bin/python

import copy
import inflection
import pprint
import requests
import string
import yaml

def main(denormalised, out_file):
    sdr_base_url = 'http://localhost:8080'
    basicAuth = ('user', 'password')


    swagger_template = {\
        "swagger":"2.0", \
        "info":{\
            "version":"0.0.1", \
            "title":"myProject"\
        }, \
        "host":"localhost:8080", \
        "basePath":"/", \
        "paths":None,
        "definitions":None\
        }

    sdr2swagger_datatype_map = {}
    sdr2swagger_datatype_map['boolean'] = {'type': 'boolean'}
    sdr2swagger_datatype_map['instant'] = {'type': 'string', 'format': 'date-time'}
    sdr2swagger_datatype_map['localTime'] = {'type': 'string', 'format': 'date-time'}
    sdr2swagger_datatype_map['long'] = {'type': 'integer', 'format': 'int64'}
    sdr2swagger_datatype_map['short'] = {'type': 'integer', 'format': 'int32'}
    sdr2swagger_datatype_map['string'] = {'type': 'string'}

    swagger_standard_responses = {'responses': {'200': {'description': ''}}}

    sdr_endpoints = requests.get(sdr_base_url, auth=basicAuth).json()['_links']

    sdr_alps_endpoint = sdr_endpoints['profile']['href']
    del sdr_endpoints['profile']

    swagger_definitions = {}
    for k1, v1 in sdr_endpoints.iteritems():
        sdr_endpoint_schema_url = string.split(v1['href'], '{')[0] + '/schema'
        sdr_endpoint_schema = requests.get(sdr_endpoint_schema_url, auth=basicAuth, headers={'accept': 'application/schema+json'}).json()
        model_name = string.split(sdr_endpoint_schema['name'], '.')[-1]
        swagger_definitions[model_name] = {'type': 'object', 'properties': {}}
        for k2, v2 in sdr_endpoint_schema['properties'].iteritems():
            if k2 != 'id':
                swagger_definitions[model_name]['properties'][k2] = sdr2swagger_datatype_map[v2['type']].copy()
        evoinflected_name = string.split(string.split(v1['href'], '/')[-1], '{')[0]
        swagger_definitions[model_name]['x-evoinflected-name'] = evoinflected_name
        alps_entity_url = sdr_alps_endpoint + '/' + evoinflected_name
        alps_entity_schema = requests.get(alps_entity_url, auth=basicAuth).json()
        for v3 in alps_entity_schema['descriptors'][0]['descriptors']:
            if 'rt' in v3:
                relation_entity_schema_url = string.split(v3['rt'], '#')[0] + '/schema'
                relation_schema = requests.get(relation_entity_schema_url, auth=basicAuth, headers={'accept': 'application/schema+json'}).json()
                relation_model_name = string.split(relation_schema['name'], '.')[-1]
                if denormalised:
                    item = {'$ref': '#/definitions/' + relation_model_name}
                else:
                    item = {'type': 'string'}
                if v3['name'].lower() == inflection.pluralize(relation_model_name).lower():
                    swagger_definitions[model_name]['properties'][v3['name']] = {'type': 'array', 'items': item}
                else:
                    swagger_definitions[model_name]['properties'][v3['name']] = item

    swagger_paths = {}
    for k4, v4 in swagger_definitions.iteritems():
        # get{?page,size,sort}
        verb = 'get'
        trailing_path = ''
        spec = {'tags': [k4], 'parameters': [\
            {'in': 'query', 'name': 'page', 'type': 'integer', 'format': 'int32', 'required': False}, \
            {'in': 'query', 'name': 'size', 'type': 'integer', 'format': 'int32', 'required': False}, \
            {'in': 'query', 'name': 'sort', 'type': 'integer', 'format': 'int32', 'required': False}, \
            ]}
        spec.update(copy.deepcopy(swagger_standard_responses))
        swagger_paths.setdefault('/' + v4['x-evoinflected-name'] + trailing_path, {}).update({verb: spec})
        # get/{id}
        verb = 'get'
        trailing_path = '/{id}'
        spec = {'tags': [k4], 'parameters': [\
            {'in': 'path', 'name': 'id', 'type': 'integer', 'format': 'int64', 'required': True}, \
            ]}
        spec.update(copy.deepcopy(swagger_standard_responses))
        swagger_paths.setdefault('/' + v4['x-evoinflected-name'] + trailing_path, {}).update({verb: spec})
        # delete
        verb = 'delete'
        trailing_path = '/{id}'
        spec = {'tags': [k4], 'parameters': [\
            {'in': 'path', 'name': 'id', 'type': 'integer', 'format': 'int64', 'required': True}, \
            ]}
        spec.update(copy.deepcopy(swagger_standard_responses))
        swagger_paths.setdefault('/' + v4['x-evoinflected-name'] + trailing_path, {}).update({verb: spec})
        # post
        verb = 'post'
        trailing_path = ''
        spec = {'tags': [k4], 'parameters': [\
            {'in': 'body', 'name': 'body', 'schema': {'$ref': '#/definitions/' + k4}}, \
            ]}
        spec.update(copy.deepcopy(swagger_standard_responses))
        swagger_paths.setdefault('/' + v4['x-evoinflected-name'] + trailing_path, {}).update({verb: spec})
        # put/{id}
        verb = 'put'
        trailing_path = '/{id}'
        spec = {'tags': [k4], 'parameters': [\
            {'in': 'path', 'name': 'id', 'type': 'integer', 'format': 'int64', 'required': True}, \
            {'in': 'body', 'name': 'body', 'schema': {'$ref': '#/definitions/' + k4}}, \
            ]}
        spec.update(copy.deepcopy(swagger_standard_responses))
        swagger_paths.setdefault('/' + v4['x-evoinflected-name'] + trailing_path, {}).update({verb: spec})
        # scan search
        search_options_url = string.split(sdr_endpoints[v4['x-evoinflected-name']]['href'], '{')[0] + '/search'
        search_options = requests.get(search_options_url, auth=basicAuth).json()['_links']
        for k5, v5 in search_options.iteritems():
            search_params_raw = string.split(string.split(string.split(v5['href'], '{?')[1], '}')[0], ',')
            search_params = []
            for v6 in search_params_raw:
                if 'type' not in swagger_definitions[k4]['properties'][v6]:
                    v6_camelcase = v6[0].upper() + v6[1:]
                    search_param_type = swagger_definitions[v6_camelcase]['properties']['name']['type']
                else:
                    search_param_type = swagger_definitions[k4]['properties'][v6]['type']
                search_param = {'in': 'query', 'name': v6, 'required': True, 'allowEmptyValue': True, 'type': search_param_type}
                if 'format' in swagger_definitions[k4]['properties'][v6]:
                    search_param['format'] = swagger_definitions[k4]['properties'][v6]['format']
                search_params.append(search_param)
            verb = 'get'
            trailing_path = '/search/' + k5
            spec = {'tags': [k4], 'parameters': search_params}
            spec.update(copy.deepcopy(swagger_standard_responses))
            swagger_paths.setdefault('/' + v4['x-evoinflected-name'] + trailing_path, {}).update({verb: spec})

    swagger_template['definitions'] = swagger_definitions
    swagger_template['paths'] = swagger_paths

    yaml.safe_dump(swagger_template, file(out_file, 'w'), default_flow_style=False)

main(False, '../resources/static/swagger-ui-normalised.yml')
main(True, '../resources/static/swagger-ui-denormalised.yml')
