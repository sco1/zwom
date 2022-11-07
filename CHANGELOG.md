# Changelog
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`<major>`.`<minor>`.`<patch>`)

## [vNext]
* #7 Add inline comment support
* #8 Add metasyntax (`START_REPEAT`, `END_REPEAT`) for workout block group repetition
* (Internal) `ZWOMValidator.validate_scanned` now returns a list of validated blocks

## [v0.2.0]
### Added
* Add ZWOM file validation
* Add `COOLDOWN` tag as a `RAMP` alias
* #3 Add Power Zone specification as an acceptable power syntax
* Add initial XML serialization
* Add initial CLI commands (`zwom single`, `zwom batch`)

### Changed
* Minimum Python version is now 3.11
* Rename the `COUNT` keyword to `REPEAT` to align with Zwift's terminology
* Unify on `*.zwom` (ZWOM) verbiage for the minilang to deconflict from Zwift's workout format (`*.zwo`)

## [v0.1.0]
Initial release
