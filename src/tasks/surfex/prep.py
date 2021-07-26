# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from footprints import FPDict

import vortex
from vortex import toolbox
from vortex.layout.nodes import Task, Family, Driver
from common.util.hooks import update_namelist
import davai

from davai_taskutil.mixins import DavaiIALTaskMixin, IncludesTaskMixin


class Prep(Task, DavaiIALTaskMixin, IncludesTaskMixin):

    experts = [FPDict({'kind':'fields_in_file'})]
    lead_expert = experts[0]

    def _flow_input_pgd_block(self):
        return '.'.join(['pgd',
                         self.conf.geometry.tag])

    def output_block(self):
        return '.'.join([self.tag,
                         self.conf.geometry.tag])

    def process(self):
        self._wrapped_init()
        self._notify_start()

        # 0./ Promises
        if 'early-fetch' in self.steps or 'fetch' in self.steps:
            self._wrapped_promise(**self._promised_expertise())
            #-------------------------------------------------------------------------------

        # 1.1.0/ Reference resources, to be compared to:
        if 'early-fetch' in self.steps or 'fetch' in self.steps:
            self._wrapped_input(**self._reference_continuity_expertise())
            #TODO: ref IC file # self._wrapped_input(**self._reference_continuity_listing())
            #-------------------------------------------------------------------------------

        # 1.1.1/ Static Resources:
        if 'early-fetch' in self.steps or 'fetch' in self.steps:
            self._load_usual_tools()  # LFI tools, ecCodes defs, ...
            #-------------------------------------------------------------------------------
            self._wrapped_input(
                role           = 'CoverParams',
                format         = 'foo',
                genv           = self.conf.commonenv,
                kind           = 'coverparams',
                local          = 'ecoclimap_covers_param.tgz',
                source         = 'ecoclimap',
            )
            #-------------------------------------------------------------------------------
            self._wrapped_input(
                role           = 'Initial Clim',  # PGD
                format         = 'fa',
                genv           = self.conf.appenv,
                geometry       = self.conf.prep_initial_geometry,
                kind           = 'pgdfa',
                local          = 'PGD1.[format]',
                gvar           = 'pgd_fa_[geometry::tag]',
            )
            if self.conf.prep_source_pgd == 'static':
                # else: 2.1
                self._wrapped_input(
                    role           = 'Target Clim',  # PGD
                    format         = 'fa',
                    genv           = self.conf.appenv,
                    geometry       = self.conf.geometry,
                    kind           = 'pgdfa',
                    local          = 'PGD.[format]',
                    gvar           = 'pgd_fa_[geometry::tag]',
                )

            #-------------------------------------------------------------------------------

        # 1.1.2/ Static Resources (namelist(s) & config):
        if 'early-fetch' in self.steps or 'fetch' in self.steps:
            self._wrapped_input(
                role           = 'Namelist',
                binary         = 'arpifs',
                format         = 'ascii',
                genv           = self.conf.appenv,
                intent         = 'inout',
                kind           = 'namelist',
                local          = 'OPTIONS.nam',
                source         = 'SFX/{}/namel_prep'.format(self.conf.model),
            )
            #-------------------------------------------------------------------------------

        # 1.1.3/ Static Resources (executables):
        if 'early-fetch' in self.steps or 'fetch' in self.steps:
            #-------------------------------------------------------------------------------
            tbx = self._wrapped_executable(
                role           = 'Binary',
                binmap         = 'gmap',
                format         = 'bullx',
                kind           = 'prep',
                local          = 'PREP.X',
                remote         = self.guess_pack(),
                setcontent     = 'binaries',
            )
            #-------------------------------------------------------------------------------

        # 1.2/ Flow Resources (initial): theoretically flow-resources, but statically stored in input_shelf
        if 'early-fetch' in self.steps or 'fetch' in self.steps:
            self._wrapped_input(
                role           = 'Surface Initial Conditions',
                block          = 'forecast',
                experiment     = self.conf.input_shelf,
                format         = 'fa',
                geometry       = self.conf.prep_initial_geometry,
                kind           = 'historic',
                local          = 'PREP1.[format]',
                model          = 'surfex',
                origin         = 'forecast',
                term           = 0,
                vapp           = self.conf.shelves_vapp,
                vconf          = self.conf.shelves_vconf,
            )
            #-------------------------------------------------------------------------------

        # 2.1/ Flow Resources: produced by another task of the same job
        if 'fetch' in self.steps:
            if self.conf.prep_source_pgd == 'flow':
                # else: 1.1.1
                self._wrapped_input(
                    role           = 'Target Clim',  # PGD
                    block          = self._flow_input_pgd_block(),
                    experiment     = self.conf.xpid,
                    format         = 'fa',
                    geometry       = self.conf.geometry,
                    kind           = 'pgdfa',
                    local          = 'PGD.[format]',
                )
            #-------------------------------------------------------------------------------

        # 2.2/ Compute step
        if 'compute' in self.steps:
            self.sh.title('Toolbox algo = tbalgo')
            tbalgo = toolbox.algo(
                crash_witness  = True,
                engine         = 'blind',
                kind           = 'prep',
                underlyingformat = 'fa',
            )
            print(self.ticket.prompt, 'tbalgo =', tbalgo)
            print()
            self.component_runner(tbalgo, tbx)
            #-------------------------------------------------------------------------------
            self.run_expertise()
            #-------------------------------------------------------------------------------

        # 2.3/ Flow Resources: produced by this task and possibly used by a subsequent flow-dependant task
        if 'backup' in self.steps:
            #-------------------------------------------------------------------------------
            self._wrapped_output(
                role           = 'Target Surface Conditions',
                block          = self.output_block(),
                experiment     = self.conf.xpid,
                format         = 'fa',
                kind           = 'ic',
                local          = 'PREP1_interpolated.[format]',
            )
            #-------------------------------------------------------------------------------

        # 3.0.1/ Davai expertise:
        if 'late-backup' in self.steps or 'backup' in self.steps:
            self._wrapped_output(**self._output_expertise())
            self._wrapped_output(**self._output_comparison_expertise())
            #-------------------------------------------------------------------------------

        # 3.0.2/ Other output resources of possible interest:
        if 'late-backup' in self.steps or 'backup' in self.steps:
            self._wrapped_output(**self._output_listing())
            #-------------------------------------------------------------------------------
