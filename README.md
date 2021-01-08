Collibra
--------
This package can be used to update the bronze layer on collibra:
* dev: https://adidas-dev.collibra.com/signin
* prod: https://adidas.collibra.com/signin

It makes use of the collibra rest api:
* https://adidas-dev.collibra.com/docs/index.html

Installation
------------
```
pip install git+https://github.com/runtastic/collibra-api-wrapper.git
```

Collibra - cli
--------------
The package provides two commands that can be run from the terminal:
* Update Data Elements and Relations (dqr->de, de->de):
This command walks through a json schema and creates the data elements (attributes in schema) + hierachical relations.
```
update_de_and_relations <COLLIBRA_URL> <COLLIBRA_USER> <COLLIBRA_PASSWORD> <SCHEMA_FOLDER> <SCHEMA_NAME>
```

* Update Data Elements and Relations (dqr->de, de->de):
This command walks through a json schema and creates the data elements (attributes in schema) + hierachical relations.
```
update_dqr <COLLIBRA_URL> <COLLIBRA_USER> <COLLIBRA_PASSWORD> <FILE_FOLDER>
```

with:
* COLLIBRA_URL: 
    * dev: https://adidas-dev.collibra.com/rest/2.0
    * prd: https://adidas.collibra.com/rest/2.0
    
* COLLIBRA_USER + COLLIBRA_PASSWORD: ask @phb or @nil

* SCHEMA_FOLDER: where to find the json schema
    
* SCHEMA_NAME: filename of the json schema (without json extension!)

* FILE_FOLDER: where to find the python file containing the anonymization rules (file: operator.py)


Communities
-----------
We are updating assets inside the "runtastic" community:

https://university.collibra.com/knowledge/collibra-body-of-knowledge/data-governance-operating-model/organizational-concepts/communities/

Domains
-------
Inside our "runtastic" community we have several domains:

https://university.collibra.com/knowledge/collibra-body-of-knowledge/data-governance-operating-model/organizational-concepts/domain-types/

Assets
------
Each asset belongs to a domain. Assets are specific (like Table, Row, Column,....), there are many predefined assets available.
Assets can be related to other assets (e.g. Data Element targets Data Element).

https://university.collibra.com/knowledge/collibra-body-of-knowledge/data-governance-operating-model/structural-concepts/asset-types/


Attributes
----------
Assets can have multiple Attributes (e.g. Tag, Description, ....)

https://university.collibra.com/knowledge/collibra-body-of-knowledge/data-governance-operating-model/structural-concepts/attribute-types/

Relations
---------
Relations can be defined between two assets (e.g. Data Quality Rule governs Data Element)

https://university.collibra.com/knowledge/collibra-body-of-knowledge/data-governance-operating-model/structural-concepts/relation-types/