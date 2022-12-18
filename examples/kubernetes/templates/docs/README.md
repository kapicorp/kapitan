{% set p = inventory.parameters %}
# {{p.target_name}}

|               |                     |
|---------------|---------------------|
| **Target**    | {{ p.target_name }} |
| **Namespace** | `{{p.namespace}}`   |

{% if p.components is defined %}
## Components
| Component Name | Documentation                                      |
|----------------|----------------------------------------------------|
{% for component in p.components|sort %}
| {{component}}  | [{{component}}-readme.md]({{component}}-readme.md) |
{% endfor %}
{% endif %}