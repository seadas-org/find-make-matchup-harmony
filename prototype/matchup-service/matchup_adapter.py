# harmony_service_example/matchup_adapter.py

from typing import List
from harmony import BaseHarmonyAdapter
from harmony.util import download                # name may differ; check example
from matchup_engine import MatchupConfig, run_matchup

class MatchupAdapter(BaseHarmonyAdapter):

        def construct_config(self, job) -> MatchupConfig:
                    # job should be Harmony job model; pull your custom params out of it
                            params = job['params'] if isinstance(job, dict) else job.params
                                    # choose names that match however you plan to call the service
                                            return MatchupConfig(
                                                                time_tolerance_sec=float(params.get('time_tolerance_sec', 1800)),
                                                                            space_tolerance_km=float(params.get('space_tolerance_km', 5.0)),
                                                                                        max_secondary_per_primary=int(params.get('max_secondary_per_primary', 1)),
                                                                                                    primary_variables=params.get('primary_variables', []),
                                                                                                                secondary_variables=params.get('secondary_variables', []),
                                                                                                                        )

                                                def split_primary_secondary(self, granule_paths: List[str]):
                                                            # For a first cut, assume:
                                                                    #   - first input granule is primary
                                                                            #   - remaining are secondaries
                                                                                    # Later you can use roles, collections, etc.
                                                                                            primary = granule_paths[0]
                                                                                                    secondary = granule_paths[1:]
                                                                                                            return primary, secondary

                                                                                                            def process_item(self, item, source):
                                                                                                                        """
                                                                                                                                Called by the base class for each input STAC item.
                                                                                                                                        Should return a new STAC item describing the matchup output.
                                                                                                                                                """
                                                                                                                                                        job = self.message  # full Harmony job context
                                                                                                                                                                cfg = self.construct_config(job)

                                                                                                                                                                        # 1. Download input data to local disk
                                                                                                                                                                                #    The example service shows the recommended way; this is conceptual:
                                                                                                                                                                                        granule_paths = self.download(item)   # check exact name in example

                                                                                                                                                                                                primary_path, secondary_paths = self.split_primary_secondary(granule_paths)

                                                                                                                                                                                                        # 2. Decide where to write output
                                                                                                                                                                                                                out_dir = self.staging_location  # from BaseHarmonyAdapter
                                                                                                                                                                                                                        out_path = out_dir / "matchups.csv"

                                                                                                                                                                                                                                # 3. Run the core algorithm
                                                                                                                                                                                                                                        run_matchup(primary_path, secondary_paths, cfg, str(out_path))

                                                                                                                                                                                                                                                # 4. Create a STAC item for the output and return it
                                                                                                                                                                                                                                                        #    There are helpers in the service-lib to do this;
                                                                                                                                                                                                                                                                #    mirror the pattern from the example subsetter.
                                                                                                                                                                                                                                                                        output_item = self.create_stac_item_for_file(
                                                                                                                                                                                                                                                                                            item=item,
                                                                                                                                                                                                                                                                                                        path=str(out_path),
                                                                                                                                                                                                                                                                                                                    mime_type="text/csv"
                                                                                                                                                                                                                                                                                                                            )
                                                                                                                                                                                                                                                                                return output_item

