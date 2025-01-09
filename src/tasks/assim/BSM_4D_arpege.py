# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import vortex
from vortex import toolbox
from vortex.layout.nodes import Driver, Family, LoopFamily

from .raw2odb.batodb import BatorODB
from .screenings.screeningCNT0 import Screening as ScreeningCNT0
from .screenings.screeningOOPS import Screening as ScreeningOOPS
from .minims.minimCNT0 import Minim as MinimCNT0
from .minims.minimOOPS import Minim as MinimOOPS
from .minims.Analyse4dvar import Analyse4dvar
from .opobs.Htlad import Htlad 

def setup(t, **kw):
    return Driver(tag='drv', ticket=t, options=kw, nodes=[
        Family(tag='arpege', ticket=t, nodes=[
            Family(tag='4dvar6h', ticket=t, nodes=[
                Family(tag='default_compilation_flavour', ticket=t, nodes=[
                    BatorODB(tag='batodb', ticket=t, **kw),
                    # delayed_fail to let the OOPS family run before raising error
                    Family(tag='cnt0', ticket=t, on_error='delayed_fail', nodes=[
                        ScreeningCNT0(tag='screeningCNT0', ticket=t, **kw),
                        MinimCNT0(tag='minimCNT0', ticket=t, **kw),
                        ], **kw),
                    Family(tag='oops', ticket=t, nodes=[
                        Family(tag='seq', ticket=t, on_error='delayed_fail', nodes=[
                            ScreeningOOPS(tag='screeningOOPS', ticket=t, **kw),
                            MinimOOPS(tag='minimOOPS', ticket=t, **kw),
                            Htlad(tag='test_adjoint', ticket=t, **kw),                                                        
                            ], **kw),
                        Family(tag='allinone', ticket=t, nodes=[
                            Analyse4dvar(tag='Analyse4dvar', ticket=t, **kw),
                            ], **kw),
                        ], **kw),
                    ], **kw),
                ], **kw),
            ], **kw),
        ],
    )

