# Changelog

## `v0.7.0`


### Features

* :feat(culture): Add `StemCell` table to accommodate an alternative experimental protocol 
* :update(README): Add instructions for local testing of SciViz
* :fix(webapps): Add platform and update version of `pharus` and `fakeservices.datajoint.io` in `docker-compose.yaml`
* :feat(webapps): Add route, table and form for new table `StemCell` in `utah_organoids_specsheet.yaml`


## `v0.6.1`


### Bug Fixes

* :bug: bug fix in spike_sorting.ipynb ([24ce9b3](https://github.com/dj-sciops/utah_organoids/commit/24ce9b367ea43c89edb35e355bcb8968aa892e65))


### Styles

* format fix ([81dad78](https://github.com/dj-sciops/utah_organoids/commit/81dad7846a360c408475c17d4389cd4f4a8c724c))


## `v0.6.0`


### Features

* :sparkles: add auto_insert_sessions to ingestion_utils.py ([e2d2a2c](https://github.com/dj-sciops/utah_organoids/commit/e2d2a2c0ff117f49e36a6e2708d709d3af817ef7))
* :sparkles: add get_workflow_operation_overview ([d088afc](https://github.com/dj-sciops/utah_organoids/commit/d088afc7db85b891b47442f887fb3866eee0f683))


### Code Refactoring

* :sparkles: move example usage of create_session to ingestion_utils.py ([b7e4875](https://github.com/dj-sciops/utah_organoids/commit/b7e4875d8b48a6c070d16e26768b09d4c852c371))



## `v0.5.1`


### Bug Fixes

* :ambulance: update path store variables ([98b53ee](https://github.com/dj-sciops/utah_organoids/commit/98b53ee3014b394dfa4e8c9ddbf16b89e65a547a))


### Build Systems

* :construction_worker: update docker for spike sorting ([3919dff](https://github.com/dj-sciops/utah_organoids/commit/3919dff9135d049075b837738ac6dd83cd8dba89))
* :construction_worker: update spike sorting docker ([ac2b63a](https://github.com/dj-sciops/utah_organoids/commit/ac2b63a10d084ca2620fb73367832c4c25ee0ac0))


## `v0.5.0`


### Features

* :sparkles: add session_type to create_sessions ([969d993](https://github.com/dj-sciops/utah_organoids/commit/969d99313bb7159474bd190eabe575d031b5f12f))
* :sparkles: resolve duplicate file download issue ([ee5c8cd](https://github.com/dj-sciops/utah_organoids/commit/ee5c8cdab032e26992b97a7f5c07d5dc099aa522))


### Code Refactoring

* :fire: remove log_message from FileProcessing ([b594221](https://github.com/dj-sciops/utah_organoids/commit/b594221471aac429718cc879b6ec1ce156d65065))


## `v0.4.3`


### Bug Fixes

* :bug: fix f string error in exception ([e058114](https://github.com/dj-sciops/utah_organoids/commit/e05811493c4cbef643df5ec7d4079ee81e6d70fa))


## `v0.4.2`


### Bug Fixes

* :bug: fix bugs in ingestion scripts ([2eb63af](https://github.com/dj-sciops/utah_organoids/commit/2eb63afcbffbc823017124dc4f0ce2f4bedb31d3))


### Build Systems

* :heavy_plus_sign: add spikeinterface & probeinterface dependency ([30a49c7](https://github.com/dj-sciops/utah_organoids/commit/30a49c7dfc51e2f4e4babd07a22c46b0003e05ad))


## `v0.4.1`


### Bug Fixes

* :bug: fix dj stores ([36c57a1](https://github.com/dj-sciops/utah_organoids/commit/36c57a1bb1614bcbeda896a07256bfe9ce457156))
* :bug: set s3 stores config from env ([4729e85](https://github.com/dj-sciops/utah_organoids/commit/4729e85916d673130af620426609b3c4cc20100c))


### Code Refactoring

* :art: update to use FileProcessing ([2fe6add](https://github.com/dj-sciops/utah_organoids/commit/2fe6add8c2e5ae9a2701a9042e74593cf6fff300))


## `v0.4.0`


### Features

* :sparkles: add insert_session.ipynb for session insertion ([8ff24aa](https://github.com/dj-sciops/utah_organoids/commit/8ff24aa7499a59c44a854eea0e7d77f4d4fc15e2))
* :sparkles: update Experiment & ExperimentDirectory ([eb2afe4](https://github.com/dj-sciops/utah_organoids/commit/eb2afe4505498a9e1eb9a9b1a4e6b8dc8339e1ab))


### Bug Fixes

* :bug: fix Drug dependency error ([edae3a3](https://github.com/dj-sciops/utah_organoids/commit/edae3a30ebf789a061534588842e44669ace2250))


### Reverts

* :rewind: recover ExperimentDirectory ([55309dc](https://github.com/dj-sciops/utah_organoids/commit/55309dcad30ea6a3d0d846527e597cafe577e450))


### Build Systems

* :construction_worker: update github workflow ([515b02c](https://github.com/dj-sciops/utah_organoids/commit/515b02cd13295fc6164a9d1844743a77ebe8d901))
* :pushpin: python 3.9 ([81b96e4](https://github.com/dj-sciops/utah_organoids/commit/81b96e448bf9ccb83d691946ba584555581787a8))


## `v0.3.0`


### Features

* :art: update lfp_ingestion.ipynb ([7c53a07](https://github.com/dj-sciops/utah_organoids/commit/7c53a07a18fc54868daee49cb7b2867dc64d24e2))
* :sparkles: add create_dj_config.sh ([61571de](https://github.com/dj-sciops/utah_organoids/commit/61571deb20f6107eb4b0eab0a7d26b914f921767))
* :sparkles: add Drug table ([e219813](https://github.com/dj-sciops/utah_organoids/commit/e21981359c4de768fba3cd7079368d1107009f08))
* :sparkles: add get_channel_to_electrode_map in helpers.py ([5ebffa8](https://github.com/dj-sciops/utah_organoids/commit/5ebffa84dd0e35280bd53d822242df283480b784))
* :sparkles: add get_repo_dir ([62b225a](https://github.com/dj-sciops/utah_organoids/commit/62b225ae9256f0f15a3c7c7db31d16a9c5ca84cc))
* :sparkles: add ingestion.py ([fefb3b8](https://github.com/dj-sciops/utah_organoids/commit/fefb3b8b744886e819d731e25967fe6d88af6c91))
* :sparkles: add used_electrodes in ephys_session.yml ([695f90e](https://github.com/dj-sciops/utah_organoids/commit/695f90e9c34f7acf47ef5dece360933156dca03f))
* :sparkles: change Experiment to Organoid ([021df59](https://github.com/dj-sciops/utah_organoids/commit/021df59f7a14109269e03036225516c8023adaa5))
* :sparkles: make OrganoidCulture.Condition part table ([63fd30a](https://github.com/dj-sciops/utah_organoids/commit/63fd30ae86f331a17a1700f80a5750dccb111d95))
* :sparkles: update Experiment & ExperimentDirectory ([957d488](https://github.com/dj-sciops/utah_organoids/commit/957d488abfbe02e10a46193842c29f3e982062b8))
* :sparkles: update get_channel_to_electrode_map ([4ab0149](https://github.com/dj-sciops/utah_organoids/commit/4ab0149259a825f130b943afa47d34d34310adad))
* update | add yml files for meta data insertion ([568a701](https://github.com/dj-sciops/utah_organoids/commit/568a701bee16bfbe1e49c34a5fc21ea8c8219aae))


### Bug Fixes

* :ambulance: update ingestion helper functions to reflect changes in yml ([9ed0791](https://github.com/dj-sciops/utah_organoids/commit/9ed0791e1acae4d1b654e4d2e574c4320b0a5110))
* :bug: fix channel_id to channel ([4841eb9](https://github.com/dj-sciops/utah_organoids/commit/4841eb9b5e9e1cec6b93a6e00d0a89c3c90e25ff))
* :bug: fix naming & import erros ([f55ed6e](https://github.com/dj-sciops/utah_organoids/commit/f55ed6e9b96cf2bbeb5916ae608994339f6a51ed))
* :bug: fix regex bugs in pre-commit ([2c4fe61](https://github.com/dj-sciops/utah_organoids/commit/2c4fe61576df2b3f6415310ecfe744a478667dd0))


### Reverts

* :rewind: revert some changes to culture schema ([94c8d6a](https://github.com/dj-sciops/utah_organoids/commit/94c8d6a20c74368f338e971360d8b5aa910ea11b))


### Styles

* :ambulance: update .yml data files for starting ingestion ([2a2b91a](https://github.com/dj-sciops/utah_organoids/commit/2a2b91ac99eabd223a683f59e8a66c3603eeede0))


### Code Refactoring

* :art: improve probe.yml ([e2b7d87](https://github.com/dj-sciops/utah_organoids/commit/e2b7d8737d48f34a85eb800edd2c659f9bc50fca))
* :recycle: move ingestion functions to helpers.py ([cafc496](https://github.com/dj-sciops/utah_organoids/commit/cafc496fd68e8092fe83d78e646984fa21dd5169))
* :recycle: update path.py ([fb032da](https://github.com/dj-sciops/utah_organoids/commit/fb032da491586ead74f590ac2b74764a56ff278c))


### Tests

* :sparkles: add pytest folder ([3fdcecf](https://github.com/dj-sciops/utah_organoids/commit/3fdcecf2959b3c578d14f565339dcb160a7b15a4))


### Continuous Integration

* :construction_worker: add github workflow ([da36a2d](https://github.com/dj-sciops/utah_organoids/commit/da36a2dd17a611df3075625aafb68b86b1de1668))


### Documentation

* :memo: update README.md ([a487540](https://github.com/dj-sciops/utah_organoids/commit/a48754071941cabc9e826e17aed45f5b50b8583b))
* :memo: update README.md ([70faabd](https://github.com/dj-sciops/utah_organoids/commit/70faabd4d13c3b3b86bec128c587e2f64585fce1))


### Build Systems

* :construction_worker: replace setup.py with pyproject.toml ([12c796c](https://github.com/dj-sciops/utah_organoids/commit/12c796ccc4f30fdccc1c82dec84a526d818d43db))
* :construction_worker: update dependency builds ([c6f6ec9](https://github.com/dj-sciops/utah_organoids/commit/c6f6ec9cf916999306847405e7e6a39a62f09695))
* :construction_worker: update requirements.txt ([acf5501](https://github.com/dj-sciops/utah_organoids/commit/acf5501ba9bd803d3eae4dc3db4f8313e0e42734))


Observes [Semantic Versioning](https://semver.org/spec/v2.0.0.html) standard and
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) convention.

## 0.2.1

+ Update - Protocol culture diagram
+ Update - `lineage.py` schema
+ Update - Rename `induction.py` to `culture.py`
+ Update - Consolidate tables in the `culture.py` schema and update the SciViz spec sheet accordingly
+ Update - `pipeline/ephys.py` to remove insertion of entries to the `ProbeType`, `Probe` and `ElectrodeConfig` tables

## 0.2.0

+ Update - SciViz layout to display table view and form on same tab
+ Update - Convert datatypes to `unsigned`

## 0.1.2

+ Update - SciViz version

## 0.1.1

+ Fix - SciViz mapping input

## 0.1.0

+ First pass
