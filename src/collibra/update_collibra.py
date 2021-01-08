import os
import ast
import sys
import json
import pprint
import logging
import argparse

from collibra.collibra_api import Collibra
from collibra import __version__


sep = " > "


def load_json(fn):
    with open(fn) as fi:
        return json.load(fi)


def findall(obj, k_parent, k, cats, cat):
    """
    Recursive function to retrieve all relevant key-value pairs. Some keys may occur multiple times,
    so the variable cat will hold the most meaningful parent variable for distinguishing
    Args:
        obj (dict, list): current json object to parse
        k_parent (str): parent key of current json object (obj)
        k (str): key to search for
        cats (tuple): tuple of keys that can not act as a top level parent key (cat)
        cat (str): top level parent key
    Returns:
        parent key, value of the searched key, top level parent key
    """
    if isinstance(obj, dict):
        keys = list(obj.keys())
        if k in keys:
            # reached an object with anonymization rule
            yield k_parent, obj[k], cat
        if len(keys) == 1 and 'type' in keys:
            # reached a final object without anonymization rule
            yield k_parent, None, cat
        if k_parent not in cats and k_parent != '' and len(keys) > 1:
            # define new parent object
            cat = cat + "." + k_parent
        for k1 in obj:
            k_parent = k1
            yield from findall(obj[k1], k_parent, k, cats, cat)


def parse_dqr(fn_temp, fn_input, classname="AnonymizationOperators"):
    """
    Parse a python module and save an updated json file containing all available functions inside a specific class
    Args:
        fn_temp (str): path of template file (json)
        fn_input (str): path of python module containing the anonymization rules
        fn_output (dict): generated python dictionary for updating entities on Collibra
        classname (str): name of the class to be parsed in fn_input
    """
    assets = []
    dqr_temp = load_json(fn_temp)

    with open(fn_input, 'r') as fi:
        tree = ast.parse(fi.read())
    class_body = [obj for obj in tree.body if isinstance(obj, ast.ClassDef) and obj.name == classname][0].body
    functions = [fu for fu in class_body if isinstance(fu, ast.FunctionDef) and fu.name != "__init__"]
    for func in functions:
        assets.append({'Name': func.name, 'Description': ast.get_docstring(func).split("\n")[0]})

    dqr_temp.update({'assets': assets})
    return dqr_temp


def parse_fields_and_relations(fn_dqr_rel_temp, fn_de_temp, fn_de_rel_temp, fn_input,
                               top_level, rule_key='x-anonymize-operation', cats=('properties')):
    """
    Parse a json file and return updated dictionaries
    Args:
        fn_dqr_rel_temp (str): path to template file (json) for relations between Data Quality Rules and Data Elements
        fn_de_temp (str): path to template file (json) for Data Elements
        fn_de_rel_temp (str): path to template file (json) for relations between 2 Data Elements
        fn_input (str): path of json file containing fields and rules -> to be parsed
        top_level (str): key for top level data element
        rule_key (str): relation type to search for
        cats (tuple): keys in json file to ignore/skip
    Returns:
        de_temp (dict): updated Data Element template
        de_rel_temp (dict): updated template for relations between two Data Elementsu
        dqr_rel_temp (dict): updated template for relations between Data Quality Rules and Data Elements
    """
    de_temp = load_json(fn_de_temp)
    de_rel_temp = load_json(fn_de_rel_temp)
    dqr_rel_temp = load_json(fn_dqr_rel_temp)
    de = []
    de_rel = []
    dqr_rel = []

    tree = load_json(fn_input)
    connections = []
    for field, rule, cat in findall(tree, '', rule_key, cats, ''):
        source = top_level+cat
        target = source + "." + field
        de.append({'Name': target.replace(".", sep), 'Description': field.replace(".", sep)})
        de_rel.append({'source': source.replace(".", sep), 'target': target.replace(".", sep)})
        if rule is not None:
            dqr_rel.append({'source': rule, 'target': target.replace(".", sep)})
        connections.append(source)

    # generate all containers and their relations
    containers = sorted(set(connections))
    names = []
    for c in containers:
        indices = [i for i, x in enumerate(c) if x == "."]
        indices.append(len(c))
        for ind, j in enumerate(indices):
            parent = None
            if ind > 0:
                parent = c[0:indices[ind-1]]
            name = c[0:j]
            if name not in names:
                de.append({'Name': name.replace(".", sep), 'Description': name.replace(".", sep)})
                if parent is not None:
                    de_rel.append({'source': parent.replace(".", sep), 'target': name.replace(".", sep)})
                names.append(name)

    de_temp.update({'assets': de})
    de_rel_temp.update({'relations': de_rel})
    dqr_rel_temp.update({'relations': dqr_rel})

    return de_temp, de_rel_temp, dqr_rel_temp


def update_assets(collibra_conn, assets, check_attr=False):
    """
    Update parsed assets
    Args:
        collibra_conn (Collibra): object of Collibra class used for interacting with collibra api
        assets (dict): updated asset template
        check_attr (bool): whether to update attributes (True) or not (False)
    """
    asset_type_id = collibra_conn.get_asset_type_id(assets["asset_type"])
    rt_community_id = collibra_conn.get_community_id(assets["rt_community"])
    # da_community_id = collibra_conn.get_community_id(assets["da_community"], parentId=rt_community_id)
    domain_id = collibra_conn.get_domain_id(assets["domain"], communityId=rt_community_id)

    # get all assets inside given domain
    r = collibra_conn.get_assets(domain_id)
    on_collibra = {d['name']: d for d in r}
    asset_ids, new_assets_ids = check_assets(collibra_conn, assets['assets'], domain_id, asset_type_id, on_collibra)
    if check_attr:
        check_attributes(collibra_conn, assets['assets'], asset_ids)
    else:
        if new_assets_ids is not None:
            check_attributes(collibra_conn, assets['assets'], new_assets_ids)


def update_relations(collibra_conn, relations):
    """
    Update parsed relations
    Args:
        collibra_conn (Collibra): object of Collibra class used for interacting with collibra api
        relations (dict): dictionary containing all relations that should be added on collibra
    """
    relations_already_existing = 0
    relations2create = list()

    rt_community = collibra_conn.get_community_id(relations["rt_community"])
    # da_community = collibra_conn.get_community_id(relations["da_community"], parentId=rt_community)
    source_domain = collibra_conn.get_domain_id(relations["source_domain"], communityId=rt_community)
    target_domain = collibra_conn.get_domain_id(relations["target_domain"], communityId=rt_community)

    relation_type = collibra_conn.get_available_relation_types(asset_filter=relations['relation_type'])
    relation_type_id = relation_type[0][4]

    relations_on_collibra = collibra_conn.get_relation_ids({'relationTypeId': relation_type_id})

    source_assets = collibra_conn.get_assets(source_domain)
    target_assets = collibra_conn.get_assets(target_domain)
    sources_on_collibra = {d['name']: d['id'] for d in source_assets}
    targets_on_collibra = {d['name']: d['id'] for d in target_assets}
    for relation in relations["relations"]:
        try:
            source_id = sources_on_collibra[relation['source']]
            target_id = targets_on_collibra[relation['target']]
        except KeyError:
            print('Source and/or target asset not existing!')
            continue
        if '{}/{}'.format(source_id, target_id) not in relations_on_collibra.keys():
            relation_dict = {"sourceId": source_id, "targetId": target_id}
            relation_dict.update({"typeId": relation_type_id})
            relations2create.append(relation_dict)
        else:
            relations_already_existing += 1

    if len(relations2create) > 0:
        collibra_conn.create_relations(relations2create)
    print(f'\t{len(relations2create)} relation(s) created')
    print(f'\t{relations_already_existing} relation(s) already existed')


def check_assets(collibra_conn, in_json, domain_id, asset_type_id, on_collibra):
    """
    Check if assets need to be created or if they already exist
    Args:
        collibra_conn (Collibra): object of Collibra class used for interacting with collibra api
        in_json (list): list of dictionaries containing descriptions for each asset to create/update
        domain_id (str): id of the domain the assets should be created in
        asset_type_id (str): id of the collibra asset type
        on_collibra (dict): dictionary of assets that are already on collibra
    Returns:
        asset_ids (dict): dictionary containing id for each asset
    """
    asset_ids = dict()
    assets2create = list()
    for asset in in_json:
        asset_name = asset["Name"]
        if asset_name not in on_collibra:
            a = {
                "name": asset_name,
                "domainId": domain_id,
                "typeId": asset_type_id}
            assets2create.append(a)
        else:
            asset_ids.update({asset_name: on_collibra[asset_name]['id']})

    # create assets
    new_asset_ids = None
    if len(assets2create) > 0:
        new_asset_ids = collibra_conn.create_assets(assets2create)
        asset_ids.update(new_asset_ids)
    print(f'\t{len(assets2create)} asset(s) created')

    return asset_ids, new_asset_ids


def check_attributes(collibra_conn, assets, asset_ids):
    """
    Check if attribute need to be created or updated
    """
    desc_type_ids = dict()
    attr2create = list()
    attr2update = list()

    for asset in assets:
        asset_name = asset.pop('Name')
        if asset_name not in asset_ids:
            continue
        assetId = asset_ids[asset_name]
        res = collibra_conn.get_attributes(assetId)
        existing_attrs = [e['type']['name'] for e in res]

        for attr in asset:
            if attr in existing_attrs:
                pos = existing_attrs.index(attr)
                if attr not in desc_type_ids:
                    desc_type_ids[attr] = res[pos]['type']['id']
                description = {
                    "id": res[pos]['id'],
                    "value": asset[attr]}
                attr2update.append(description)
            else:
                if attr not in desc_type_ids:
                    desc_type_ids[attr] = collibra_conn.get_attribute_type_id(attr)
                description = {
                    "assetId": assetId,
                    "typeId": desc_type_ids[attr],
                    "value": asset[attr]}
                attr2create.append(description)

    # create attributes
    if len(attr2create) > 0:
        collibra_conn.create_attributes(attr2create)
        print(f'\t{len(attr2create)} attribute(s) created')

    # update attributes
    if len(attr2update) > 0:
        collibra_conn.update_attributes(attr2update)
        print(f'\t{len(attr2update)} attribute(s) updated')


def setup(filename=False):
    parser = argparse.ArgumentParser(description="Collibra")
    parser.add_argument("COLLIBRA_URL", help="Collibra base url")
    parser.add_argument("COLLIBRA_USER", help="Username for Collibra")
    parser.add_argument("COLLIBRA_PASSWORD", help="Password for Collibra user")
    parser.add_argument("COLLIBRA_PATH", help="Path to files that need to be parsed")
    if filename:
        parser.add_argument("COLLIBRA_FILE", help="File to be parsed")
    parser.add_argument("--version", action="version", version="collibra {ver}".format(ver=__version__))
    parser.add_argument("-v", "--verbose", dest="loglevel", help="set loglevel to INFO", action="store_const",
                        const=logging.INFO)
    parser.add_argument("-vv", "--very-verbose", dest="loglevel", help="set loglevel to DEBUG", action="store_const",
                        const=logging.DEBUG)

    if filename:
        args = parser.parse_args(sys.argv[1:])
        schema_type = args.COLLIBRA_FILE
    else:
        args = parser.parse_args(sys.argv[1:5])
        schema_type = None

    collibra_conn = Collibra(args.COLLIBRA_URL, args.COLLIBRA_USER, args.COLLIBRA_PASSWORD)
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    input_path = args.COLLIBRA_PATH
    return collibra_conn, template_path, input_path, schema_type


def run_dqr():
    print('Updating Data Quality Rule Assets')
    collibra_conn, template_path, input_path, _ = setup(filename=False)
    fn_dqr_template = os.path.join(template_path, 'template_dqr.json')
    fn_dqr_parse = os.path.join(input_path, 'operators.py')
    dqr = parse_dqr(fn_dqr_template, fn_dqr_parse)
    update_assets(collibra_conn, dqr, check_attr=True)


def run_de_and_relations():
    collibra_conn, template_path, input_path, schema_type = setup(filename=True)
    # Data Elements and Relations
    fn_dqr_relation_template = os.path.join(template_path, 'template_dqr_relations.json')
    fn_de_relation_template = os.path.join(template_path, 'template_de_relations.json')
    fn_de_template = os.path.join(template_path, 'template_de.json')
    fn_parse = os.path.join(input_path, '{}.schema.json'.format(schema_type))
    de, de_rel, dqr_rel = parse_fields_and_relations(fn_dqr_relation_template, fn_de_template,
                                                     fn_de_relation_template, fn_parse, schema_type)
    # Update data elements and relations on Collibra
    print('Updating Data Element Assets')
    update_assets(collibra_conn, de)
    print('Updating Relations between Data Elements')
    update_relations(collibra_conn, de_rel)
    print('Updating Relations between Data Quality Rules and Data Elements')
    update_relations(collibra_conn, dqr_rel)


if __name__ == "__main__":
    run_dqr()
    # run_de_and_relations()

