from .raise_rule_param_invalid_error import raise_rule_param_invalid_error


_DESIGN_NOTES = """
# rules/_validations — Failure Cards of the File Rules

Plain imports, not exported from the package.

## Internal Components Registry

| Component                       | Type     | Description                                                     |
| :------------------------------ | :------- | :-------------------------------------------------------------- |
| `raise_rule_param_invalid_error`| Function | Raises `ParamError` when a rule is built with an invalid param. |
"""