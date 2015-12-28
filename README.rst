tls-cal
=======

tls-cal creates an iCal feed of when your certificates expire.

Create a YAML configuration file like:

.. code-block:: yaml

    hosts:
        - google.com
        - facebook.com
        - twitter.com
        - whitehouse.gov

And then:

.. code-block:: console

    $ python tlscal.py path/to/config.yml

Beware: this is raw, it has bugs.
