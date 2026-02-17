
===============
Encrypted Field
===============

This module enables user to store field value in encrypted form.
One or more fields can be stored inside single Encrypted Field.
Just before storing to database, fields gets serialized, and encrypted.
On the other hand, after reading, encrypted field gets decrypted and
deserialized and values are available in each field in original form.
It uses symmetrical AES encryption.

Requirements
============

    pip install cryptography

Configuration
=============
Because this module extends odoo.fields module, it needs to be loaded as server wide module.
This can be achieved by passing

    --load="web,base_encrypted_field"

or by adding following line to the server config file:

    server_wide_modules = web,base_encrypted_field

In order to set key for encryption/decryption, add following line to server config file:

    encryption_key=<YOUR_KEY>

You can generate key with python cryptography module like this:

    from cryptography.fernet import Fernet

    Fernet.generate_key().decode()

Usage
=====

Encrypted field works in such a way that it bundles other fields
that point to it by setting encrypt argument. All those fields are
becoming computed fields with inverse function, that populates
Encrypted field.

Just before storing Encrypted field to database,
its value gets encrypted, and it gets decrypted immediately after
reading from database. Encrypted field is stored in binary form.

One model can have multiple Encrypted fields without restriction,
and each Encrypted field can represent single or multiple regular
fields.

Check the TestEncrypted model from models.py to see how field
should be used.


