{% set i = inventory.parameters %}
# My Readme
This is to test unpacking of files fetched over http[s]
Target: {{ i.kapitan.vars.target }}
Compression type: {{ i.compression_type }}