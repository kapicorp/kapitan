# The OmegaConf Inventory Backend

## Overview

The OmegaConf inventory backend is a powerful alternative to reclass, offering enhanced interpolation capabilities, custom resolvers, and deferred evaluation.

!!! warning

    OmegaConf is currently in experimental mode. If you encounter unexpected errors or bugs, please let us know and create an [issue](https://github.com/kapicorp/kapitan/issues/new/choose).

## How It Works

```mermaid
flowchart TD
    A[Load Target YAML] --> B[Load Classes Recursively]
    B --> C[Merge Parameters]
    C --> D[First Resolution Pass]
    D --> E{Escaped Interpolations?}
    E -->|Yes| F[Unescape \${...} → ${...}]
    F --> G[Second Resolution Pass]
    E -->|No| H[Process Literal Markers]
    G --> H
    H --> I[Final Resolved Inventory]
    
    style D fill:#e1f5fe
    style G fill:#e1f5fe
    style H fill:#fff3e0
```

The OmegaConf backend uses a **double-pass resolution** strategy:

1. **First pass**: Resolves all standard `${...}` interpolations
2. **Second pass**: Resolves previously escaped `\${...}` interpolations (now unescaped)

This enables **deferred evaluation** - interpolations that resolve based on their final context after merging.

---

## Installation

```shell
pip install kapitan[omegaconf]
```

## Usage

### Command Line
```shell
kapitan compile --inventory-backend=omegaconf
```

### Permanent Configuration
Add to your [.kapitan config file](../commands/kapitan_dotfile.md):

```yaml
global:
  inventory-backend: omegaconf
```

---

## Quick Start Examples

### Basic Interpolation

```yaml
# inventory/targets/my-app.yml
parameters:
  app_name: my-application
  environment: production
  
  # Simple interpolation
  full_name: ${app_name}-${environment}  # → "my-application-production"
  
  # Nested access
  config:
    database:
      host: db.example.com
      port: 5432
    
  # Reference nested values with dot notation
  db_url: "postgresql://${config.database.host}:${config.database.port}"
  # → "postgresql://db.example.com:5432"
```

### Using Default Values

```yaml
parameters:
  # Provide defaults with oc.select
  timeout: ${oc.select:custom_timeout, 30}  # Uses 30 if custom_timeout not set
  
  # Environment variables with defaults
  log_level: ${oc.env:LOG_LEVEL, INFO}
```

### Deferred Evaluation with `\${...}`

Use escaped interpolations when you need values to resolve **after merging**:

```yaml
# inventory/classes/base-deployment.yml
parameters:
  deployment_template:
    name: \${parentkey:}           # Resolves to the KEY name after merge
    namespace: ${namespace}         # Resolves immediately
    
# inventory/targets/my-app.yml
parameters:
  namespace: production
  
  deployments:
    web-frontend: ${deployment_template}   # name → "web-frontend"
    api-backend: ${deployment_template}    # name → "api-backend"
```

**Result:**
```yaml
deployments:
  web-frontend:
    name: web-frontend      # Resolved from \${parentkey:}
    namespace: production
  api-backend:
    name: api-backend       # Resolved from \${parentkey:}
    namespace: production
```

---

## Built-in Resolvers

### OmegaConf Native Resolvers

| Resolver | Description | Example |
|----------|-------------|---------|
| `oc.env` | Access environment variable | `${oc.env:HOME}` |
| `oc.select` | Default value for interpolation | `${oc.select:key, default}` |
| `oc.dict.keys` | Get dictionary keys as list | `${oc.dict.keys:my_dict}` |
| `oc.dict.values` | Get dictionary values as list | `${oc.dict.values:my_dict}` |

### Key & Path Resolvers

| Resolver | Description | Example |
|----------|-------------|---------|
| `key` | Current node's key name | `${key:}` |
| `parentkey` | Parent node's key name | `${parentkey:}` |
| `fullkey` | Full path to current key | `${fullkey:}` |
| `relpath` | Convert absolute path to relative interpolation | `${relpath:some.absolute.path}` |
| `filename` | Current file's name flag | `${filename:}` |
| `parent_filename` | Parent node's filename flag | `${parent_filename:}` |
| `path` | Current file's path flag | `${path:}` |
| `parent_path` | Parent node's path flag | `${parent_path:}` |

### Conditional Resolvers

| Resolver | Description | Example |
|----------|-------------|---------|
| `if` | Return value if condition is true, else empty dict | `${if:${enabled}, {key: value}}` |
| `ifelse` | Return first value if true, else second | `${ifelse:${prod}, prod-val, dev-val}` |
| `and` | Boolean AND of all arguments | `${and:${a}, ${b}, ${c}}` |
| `or` | Boolean OR of all arguments | `${or:${a}, ${b}}` |
| `not` | Boolean NOT | `${not:${disabled}}` |
| `equal` | Check if all arguments are equal | `${equal:${env}, production}` |

### Data Transformation Resolvers

| Resolver | Description | Example |
|----------|-------------|---------|
| `merge` | Merge multiple OmegaConf objects | `${merge:${base}, ${overrides}}` |
| `dict` | Convert list of single-key dicts to one dict | `${dict:${list_of_dicts}}` |
| `list` | Convert dict to list of single-key dicts | `${list:${my_dict}}` |
| `yaml` | Render a key's value as YAML string | `${yaml:config.section}` |
| `add` | Add or concatenate two values | `${add:${a}, ${b}}` |
| `access` | Access keys containing dots | `${access:key.with.dots, subkey}` |

### Utility Resolvers

| Resolver | Description | Example |
|----------|-------------|---------|
| `escape` | Create an interpolation for next resolution pass | `${escape:some.path}` → `${some.path}` |
| `default` | Chain of fallback values using oc.select | `${default:key1, key2, fallback}` |
| `write` | Write resolved content to another inventory location | `${write:destination.path, source.path}` |
| `from_file` | Read content from a file | `${from_file:path/to/file.txt}` |

---

## Conditional Logic Examples

```yaml
parameters:
  environment: production
  enable_debug: false
  replicas: 3
  
  # Simple condition
  debug_config: ${if:${enable_debug}, {log_level: DEBUG, verbose: true}}
  # → {} (empty, because enable_debug is false)
  
  # If-else
  resource_limits: ${ifelse:${equal:${environment}, production},
    {cpu: "2", memory: "4Gi"},
    {cpu: "500m", memory: "512Mi"}
  }
  # → {cpu: "2", memory: "4Gi"} (production)
  
  # Combined conditions
  enable_monitoring: ${and:${equal:${environment}, production}, ${replicas}}
  # → true (both conditions met)
```

---

## Custom Resolvers

Create powerful custom resolvers by adding a `resolvers.py` file in your inventory directory.

### Basic Example

```python
# inventory/resolvers.py

def uppercase(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()

def prefix(text: str, prefix: str = "app") -> str:
    """Add a prefix to text."""
    return f"{prefix}-{text}"

def get_suffix(name: str) -> str:
    """Extract suffix after last hyphen."""
    return name.split("-")[-1]

# Required: Return dict of resolver_name -> function
def pass_resolvers():
    return {
        "upper": uppercase,
        "prefix": prefix,
        "get_suffix": get_suffix,
    }
```

**Usage:**
```yaml
parameters:
  app_name: my-service
  
  upper_name: ${upper:${app_name}}           # → "MY-SERVICE"
  prefixed: ${prefix:${app_name}, api}       # → "api-my-service"  
  suffix: ${get_suffix:${app_name}}          # → "service"
```

### Advanced: Accessing Root Context

Custom resolvers can access the entire inventory using the `_root_` parameter:

```python
# inventory/resolvers.py

def vault_secret(path: str, key: str, _root_) -> str:
    """Generate a Vault reference using target context."""
    target_name = _root_.target_name
    return f"?{{vaultkv:{target_name}/{path}:{key}}}"

def helm_input(component: str, _root_) -> dict:
    """Generate Helm input configuration from component settings."""
    comp = _root_[component]
    return {
        "input_type": "helm",
        "input_paths": [f"charts/{comp.chart_name}/{comp.chart_version}"],
        "output_path": f"k8s/{comp.namespace}",
        "helm_params": {
            "namespace": str(comp.namespace),
            "name": str(comp.chart_name),
        },
        "helm_values": f"\\${{{component}.helm_values}}",  # Deferred!
    }

def pass_resolvers():
    return {
        "vault": vault_secret,
        "helm_input": helm_input,
    }
```

**Usage:**
```yaml
parameters:
  target_name: my-target
  
  nginx:
    chart_name: nginx
    chart_version: "15.0.0"
    namespace: web
    helm_values:
      replicaCount: 3
  
  secrets:
    db_password: ${vault:database, password}
    # → "?{vaultkv:my-target/database:password}"
  
  kapitan:
    compile:
      - ${helm_input:nginx}
```

---

## Migration from Reclass

### Automatic Migration

```shell
kapitan compile --inventory-backend=omegaconf --migrate
```

!!! danger

    **Backup your inventory before migrating!** Use version control to easily revert changes if needed.

### What Gets Migrated

| Before (Reclass) | After (OmegaConf) |
|------------------|-------------------|
| `${path:to:key}` | `${path.to.key}` |
| `${_reclass_...}` | `${_kapitan_...}` |
| `\${escaped}` | `${tag:escaped}` |

### Manual Changes May Be Needed

- Keys containing `.` (dots) need special handling with the `access` resolver
- Some reclass-specific features like `exports` are not yet supported

---

## Differences from Reclass

### ✅ Supported
- compose-node-name
- key overwrite prefix `~`
- interpolations (with dot notation)
- relative class names
- init class files
- nested interpolations
- escaped/deferred interpolations

### ❌ Not Yet Supported
- exports
- inventory queries
- interpolation to YAML keys containing `.`

---

## Complete Example: Multi-Environment Deployment

```yaml
# inventory/classes/base/deployment.yml
parameters:
  # Template that adapts to where it's merged
  deployment_base:
    name: \${parentkey:}
    namespace: ${namespace}
    labels:
      app: \${parentkey:}
      environment: ${environment}
    
    image: ??? # Mandatory - must be set
    replicas: ${oc.select:default_replicas, 1}
    
    resources: ${ifelse:${equal:${environment}, production},
      {limits: {cpu: "2", memory: "4Gi"}},
      {limits: {cpu: "500m", memory: "512Mi"}}
    }

# inventory/classes/components/api.yml  
parameters:
  api_config:
    image: myregistry/api:${api_version}
    replicas: 3
    env:
      DATABASE_URL: ${database.url}

# inventory/targets/production.yml
classes:
  - base.deployment
  - components.api

parameters:
  environment: production
  namespace: prod
  api_version: "2.1.0"
  
  database:
    url: "postgres://prod-db:5432/app"
  
  deployments:
    api-server: ${merge:${deployment_base}, ${api_config}}
```

**Resolved Result:**
```yaml
deployments:
  api-server:
    name: api-server              # From \${parentkey:}
    namespace: prod
    labels:
      app: api-server             # From \${parentkey:}
      environment: production
    image: myregistry/api:2.1.0
    replicas: 3
    resources:
      limits:
        cpu: "2"
        memory: "4Gi"             # Production resources
    env:
      DATABASE_URL: "postgres://prod-db:5432/app"
```
