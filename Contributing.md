# Contributing

Feel free to contribute to
[zha-toolkit](https://github.com/mdeweerd/zha-toolkit).

You can contribute with regards to the documentations, examples,
blueprints, and code.

## Documentation

Not all commands are documented yet, and the existing documentation can be
improved.

The undocumented commands are mostly commands that were in
[zha_custom](https://github.com/Adminiuga/zha_custom).

Ideally you install `pre-commit` (See below)

## Coding

Because most of the code is reloaded on each call, you do not have to
restart Home Assistant on each change. That's fairly practical to adjust
existing functionality and add new ones.

## Adding commands

A new command results in several updates to define it:

- The main handler function.\
  The ideal is to name it `<MODULE>_<ACTION>`.

The next steps are not required to get started, you can do it once you're
happy with the functionality of your new command. They are required to
properly define the new command as a HA service command:

- In `params.py`: Add the handler name as a constant.
- In `__init__.py`:
  - `SERVICE_SCHEMAS`: Add definitions of mandatory and optional
    parameters.
  - `CMD_TO_INTERNAL_MAP`: Add a mapping if the method name is not like
    `<MODULE>_<ACTION>`.
- In `services.yaml`:
  - Add a new entry (alphabetically located) to define the UI fields for
    service calls.

You can check that these updates are correct by calling the service
`zha_toolkit.register_services` which will reload `services.yaml` and
`SERVICE_SCHEMAS` to add/redefine zha-toolkit services.

### Handler method definition:

The example below shows all the parameters you need to define for a new
handler method.

This example is located in `hello.py`. Therefore the start of the function
name (`hello`) matches the module name.

```python
async def hello_world(
    app, listener, ieee, cmd, data, service, params, event_data
):
```

Because of the naming, it is immediately available using the
`zha_toolkit.execute` service:

```yaml
service: zha_toolkit.execute
data:
  command: hello_world
  param1: content1
  param2: content2
```

Once you made the required steps to add the command as a service itself,
you can call it as:

```yaml
service: zha_toolkit.hello_world
data:
  param1: content1
  param2: content2
```

### `pre-commit`

`pre-commit` is a tool that helps execute a set of other tools prior to git
activity.

The repository is set up to format the files you're about to submit, warn
about potential errors, preventing from checking in to the main branch.

To do so, you need to set up `pre-commit` which is easy in itself.
`pre-commit` will setup the other tools.

Setting up is as simple as:

- `pip install pre-commit`
- `pre-commit install` from the base of your repository clone.

That will run automatic corrections and verifications on the code that you
are committing. If you want to skip automatic checks at some point to be
able to check in, just do: `pre-commit uninstall` at the base of the
repository. Don't forget to install it again once you committed.
