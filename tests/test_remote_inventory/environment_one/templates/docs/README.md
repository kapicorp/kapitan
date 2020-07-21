{% set i = inventory.parameters %}

# Remote Inventory Test

- Target {{ i.kapitan.vars.target }} is running.
- Fetching invenotry item from {{ i.kapitan.inventory[0].source }}