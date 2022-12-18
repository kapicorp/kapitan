| *Target* |
| -------- |
{% for target in inventory_global | sort() %}
{% set p = inventory_global[target].parameters %}
|[{{target}}](../{{target}}/docs/README.md)|
{% endfor %}
