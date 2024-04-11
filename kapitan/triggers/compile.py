import os
import logging
import tempfile
import sys
import time
import shutil
import multiprocessing

from functools import partial
from reclass.errors import NotFoundError, ReclassException

from kapitan import cached
from kapitan.utils import check_version
from kapitan.refs.base import RefController, Revealer
from kapitan.targets import search_targets, generate_inv_cache_hashes, changed_targets, load_target_inventory, schema_validate_kubernetes_output, save_inv_cache, create_validate_mapping
from kapitan.errors import CompileError, InventoryError, KapitanError
from kapitan.remoteinventory.fetch import fetch_inventories, list_sources
from kapitan.dependency_manager.base import fetch_dependencies
from kapitan.inputs.copy import Copy
from kapitan.inputs.external import External
from kapitan.inputs.helm import Helm
from kapitan.inputs.jinja2 import Jinja2
from kapitan.inputs.jsonnet import Jsonnet
from kapitan.inputs.kadet import Kadet
from kapitan.inputs.remove import Remove

logger = logging.getLogger(__name__)


def compile_target(target_obj, search_paths, compile_path, ref_controller, globals_cached=None, **kwargs):
    """Compiles target_obj and writes to compile_path"""
    start = time.time()
    compile_objs = target_obj["compile"]
    ext_vars = target_obj["vars"]
    target_name = ext_vars["target"]

    if globals_cached:
        cached.from_dict(globals_cached)

    use_go_jsonnet = kwargs.get("use_go_jsonnet", False)
    if use_go_jsonnet:
        logger.debug("Using go-jsonnet over jsonnet")

    for comp_obj in compile_objs:
        input_type = comp_obj["input_type"]
        output_path = comp_obj["output_path"]
        input_params = comp_obj.setdefault("input_params", {})

        if input_type == "jinja2":
            input_compiler = Jinja2(compile_path, search_paths, ref_controller, comp_obj)
        elif input_type == "jsonnet":
            input_compiler = Jsonnet(compile_path, search_paths, ref_controller, use_go=use_go_jsonnet)
        elif input_type == "kadet":
            input_compiler = Kadet(compile_path, search_paths, ref_controller, input_params=input_params)
        elif input_type == "helm":
            input_compiler = Helm(compile_path, search_paths, ref_controller, comp_obj)
        elif input_type == "copy":
            ignore_missing = comp_obj.get("ignore_missing", False)
            input_compiler = Copy(compile_path, search_paths, ref_controller, ignore_missing)
        elif input_type == "remove":
            input_compiler = Remove(compile_path, search_paths, ref_controller)
        elif input_type == "external":
            input_compiler = External(compile_path, search_paths, ref_controller)
            if "args" in comp_obj:
                input_compiler.set_args(comp_obj["args"])
            if "env_vars" in comp_obj:
                input_compiler.set_env_vars(comp_obj["env_vars"])
        else:
            err_msg = 'Invalid input_type: "{}". Supported input_types: jsonnet, jinja2, kadet, helm, copy, remove, external'
            raise CompileError(err_msg.format(input_type))

        input_compiler.make_compile_dirs(target_name, output_path, **kwargs)
        input_compiler.compile_obj(comp_obj, ext_vars, **kwargs)

    logger.info("Compiled %s (%.2fs)", target_obj["target_full_path"], time.time() - start)


def compile_targets(
    inventory_path, search_paths, output_path, parallel, targets, labels, ref_controller, **kwargs
):
    """
    Searches and loads target files, and runs compile_target() on a
    multiprocessing pool with parallel number of processes.
    kwargs are passed to compile_target()
    """
    # temp_path will hold compiled items
    temp_path = tempfile.mkdtemp(suffix=".kapitan")
    # enable previously compiled items to be reference in other compile inputs
    search_paths.append(temp_path)
    temp_compile_path = os.path.join(temp_path, "compiled")
    dep_cache_dir = temp_path

    updated_targets = targets
    try:
        updated_targets = search_targets(inventory_path, targets, labels)
    except CompileError as e:
        logger.error(e)
        sys.exit(1)

    # If --cache is set
    if kwargs.get("cache"):
        additional_cache_paths = kwargs.get("cache_paths")
        generate_inv_cache_hashes(inventory_path, targets, additional_cache_paths)
        # to cache fetched dependencies and inventories
        dep_cache_dir = os.path.join(output_path, ".dependency_cache")
        os.makedirs(dep_cache_dir, exist_ok=True)

        if not targets:
            updated_targets = changed_targets(inventory_path, output_path)
            logger.debug("Changed targets since last compilation: %s", updated_targets)
            if len(updated_targets) == 0:
                logger.info("No changes since last compilation.")
                return

    pool = multiprocessing.Pool(parallel)

    try:
        rendering_start = time.time()

        # check if --fetch or --force-fetch is enabled
        force_fetch = kwargs.get("force_fetch", False)
        fetch = kwargs.get("fetch", False) or force_fetch

        # deprecated --force flag
        if kwargs.get("force", False):
            logger.info(
                "DeprecationWarning: --force is deprecated. Use --force-fetch instead of --force --fetch"
            )
            force_fetch = True

        if fetch:
            # skip classes that are not yet available
            target_objs = load_target_inventory(inventory_path, updated_targets, ignore_class_notfound=True)
        else:
            # ignore_class_notfound = False by default
            target_objs = load_target_inventory(inventory_path, updated_targets)

        # append "compiled" to output_path so we can safely overwrite it
        compile_path = os.path.join(output_path, "compiled")

        if not target_objs:
            raise CompileError("Error: no targets found")

        # fetch inventory
        if fetch:
            # new_source checks for new sources in fetched inventory items
            new_sources = list(set(list_sources(target_objs)) - cached.inv_sources)
            while new_sources:
                fetch_inventories(
                    inventory_path,
                    target_objs,
                    dep_cache_dir,
                    force_fetch,
                    pool,
                )
                cached.reset_inv()
                target_objs = load_target_inventory(
                    inventory_path, updated_targets, ignore_class_notfound=True
                )
                cached.inv_sources.update(new_sources)
                new_sources = list(set(list_sources(target_objs)) - cached.inv_sources)
            # reset inventory cache and load target objs to check for missing classes
            cached.reset_inv()
            target_objs = load_target_inventory(inventory_path, updated_targets, ignore_class_notfound=False)
        # fetch dependencies
        if fetch:
            fetch_dependencies(output_path, target_objs, dep_cache_dir, force_fetch, pool)
        # fetch targets which have force_fetch: true
        elif not kwargs.get("force_fetch", False):
            fetch_objs = []
            # iterate through targets
            for target in target_objs:
                try:
                    # get value of "force_fetch" property
                    dependencies = target["dependencies"]
                    # dependencies is still a list
                    for entry in dependencies:
                        force_fetch = entry["force_fetch"]
                        if force_fetch:
                            fetch_objs.append(target)
                except KeyError:
                    # targets may have no "dependencies" or "force_fetch" key
                    continue
            # fetch dependencies from targets with force_fetch set to true
            if fetch_objs:
                fetch_dependencies(output_path, fetch_objs, dep_cache_dir, True, pool)

        logger.info("Rendered inventory (%.2fs)", time.time() - rendering_start)

        worker = partial(
            compile_target,
            search_paths=search_paths,
            compile_path=temp_compile_path,
            ref_controller=ref_controller,
            inventory_path=inventory_path,
            globals_cached=cached.as_dict(),
            **kwargs,
        )

        # compile_target() returns None on success
        # so p is only not None when raising an exception
        [p.get() for p in pool.imap_unordered(worker, target_objs) if p]

        os.makedirs(compile_path, exist_ok=True)

        # if '-t' is set on compile or only a few changed, only override selected targets
        if updated_targets:
            for target in target_objs:
                path = target["target_full_path"]
                compile_path_target = os.path.join(compile_path, path)
                temp_path_target = os.path.join(temp_compile_path, path)

                os.makedirs(compile_path_target, exist_ok=True)

                shutil.rmtree(compile_path_target)
                shutil.copytree(temp_path_target, compile_path_target)
                logger.debug("Copied %s into %s", temp_path_target, compile_path_target)
        # otherwise override all targets
        else:
            shutil.rmtree(compile_path)
            shutil.copytree(temp_compile_path, compile_path)
            logger.debug("Copied %s into %s", temp_compile_path, compile_path)

        # validate the compiled outputs
        if kwargs.get("validate", False):
            validate_map = create_validate_mapping(target_objs, compile_path)
            worker = partial(
                schema_validate_kubernetes_output,
                cache_dir=kwargs.get("schemas_path", "./schemas"),
            )
            [p.get() for p in pool.imap_unordered(worker, validate_map.items()) if p]

        # Save inventory and folders cache
        save_inv_cache(compile_path, targets)
        pool.close()

    except ReclassException as e:
        if isinstance(e, NotFoundError):
            logger.error("Inventory reclass error: inventory not found")
        else:
            logger.error("Inventory reclass error: %s", e.message)
        raise InventoryError(e.message)
    except Exception as e:
        # if compile worker fails, terminate immediately
        pool.terminate()
        logger.debug("Compile pool terminated")
        # only print traceback for errors we don't know about
        if not isinstance(e, KapitanError):
            logger.exception("\nUnknown (Non-Kapitan) error occurred:\n")

        logger.error("\n")
        if kwargs.get("verbose"):
            logger.exception(e)
        else:
            logger.error(e)
        sys.exit(1)
    finally:
        # always wait for other worker processes to terminate
        pool.join()
        shutil.rmtree(temp_path)
        logger.debug("Removed %s", temp_path)



def trigger_compile(args):
    search_paths = [os.path.abspath(path) for path in args.search_paths]

    if not args.ignore_version_check:
        check_version()

    ref_controller = RefController(args.refs_path, embed_refs=args.embed_refs)
    # cache controller for use in reveal_maybe jinja2 filter
    cached.ref_controller_obj = ref_controller
    cached.revealer_obj = Revealer(ref_controller)

    compile_targets(
        args.inventory_path,
        search_paths,
        args.output_path,
        args.parallelism,
        args.targets,
        args.labels,
        ref_controller,
        prune=(args.prune),
        indent=args.indent,
        reveal=args.reveal,
        cache=args.cache,
        cache_paths=args.cache_paths,
        fetch=args.fetch,
        force_fetch=args.force_fetch,
        force=args.force,  # deprecated
        validate=args.validate,
        schemas_path=args.schemas_path,
        jinja2_filters=args.jinja2_filters,
        verbose=hasattr(args, "verbose") and args.verbose,
        use_go_jsonnet=args.use_go_jsonnet,
        compose_node_name=args.compose_node_name,
    )

