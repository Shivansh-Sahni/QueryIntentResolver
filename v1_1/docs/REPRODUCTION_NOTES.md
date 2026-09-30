# Complete reproduction and presentation refresh

The model build command in README remains valid. To also refresh the explicit final promotion decision and polished presentation files, run:

```bash
python v1_1/scripts/materialize_frozen_suite.py
PYTHONPATH=v1_1 python -m pytest -q v1_1/tests
PYTHONPATH=v1_1 python -m qir_release.build --repo-root .
python v1_1/scripts/finalize_presentation.py
```

Or use `make -f v1_1/Makefile build` after installing pinned requirements. GitHub Actions additionally runs actual HTTP and Docker checks, emits final provenance, hashes the complete V1.1 package, and uploads both a V1.1 bundle and the complete current project source/artifacts. It does not alter `v1/`.

Generated historical metrics are not a new pristine test on each rebuild. Repeated unchanged runs verify execution reproducibility, not new independent scientific evidence. Training remains fixed; presentation changes do not change models, thresholds or gold labels.

The candidate's bundled runtime is for local demonstration and research review. No automatic promotion to a live default is authorized. See RELEASE_DECISION.md before interpreting the build output.
