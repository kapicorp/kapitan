# :kapitan-logo: **Alternative Inventory Backends**

We provide pluggable backend alternatives for the Inventory:

* `reclass`(**default**): The original kapitan inventory  (see [reclass](https://github.com/kapicorp/reclass))
* `reclass-rs`: The Rust drop in replacement (see [reclass-rs](reclass-rs.md))
* `omegaconf`: An alternative inventory solution based on [Omegaconf](https://github.com/omry/omegaconf)

You can switch the backend to by:

* (**recommended**) Define the backend in the [.kapitan config file](../commands/kapitan_dotfile.md).
* Passing the `--inventory-backend=backend` command line option when calling `kapitan`.
