.. _guide_getting_started:

Getting Started
===============
Quick way to get started with Aurora DSQL is by creating a cluster. Details on 
how to do that can be found [here](__TODO__)

"""""""""""""""""""""""""""""""""""
Define Aurora DSQL as the Engine
"""""""""""""""""""""""""""""""""""
Change the ``DATABASES`` variable in ``settings.py`` of your Django app. An example
is show below

.. code-block: python
   DATABASES = {
        'default': {
            'HOST': 'abcdefghijklmnopq123456789.dsql.us-east-1.on.aws',
            'USER': 'admin',
            'NAME': 'postgres',
            'ENGINE': 'aurora_dsql_django',
            'OPTIONS': {
                'sslmode': 'require',
                'region': 'us-east-1',
            }
        }
    }

"""""""""""""""""""""""""""""""""""
Create a sample Django application
""""""""""""""""""""""""""""""""""

TODO: Add link to user guide and/or sample code