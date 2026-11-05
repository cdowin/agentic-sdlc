# Stack pack: helm-terraform

- Status: stub

Stub: no repo has asked for it yet, so the tools below are known but not tested, and there is no Config.

## Rules

No lens lists this pack for a gate rule yet. These are the tools to map when one does.

| ID | Tool rule | Starter limit | False positives |
|---|---|---|---|
| - | `helm lint` | no error | a chart that needs values only the deploy supplies |
| - | `kubeconform` | valid manifests | a custom resource with no schema |
| - | `tflint` | no error | a rule a team turns off on purpose |
| - | `checkov` | no failed check | a check a team accepts with a written reason |
