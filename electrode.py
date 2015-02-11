from __future__ import division

import numpy as np
from traits.api import (HasTraits, List, Float, Tuple, Instance, Bool, Str, 
    Int, Either, Property, Method, on_trait_change, Any, Enum, Button)
from traitsui.api import (View, Item, HGroup, Handler, CSVListEditor, VGroup,
    InstanceEditor, Group, OKCancelButtons, TableEditor, ObjectColumn,
    TextEditor, OKButton, CheckListEditor, Label, Action, ListStrEditor)
from traitsui.message import error as error_dialog

class Electrode(HasTraits):
#    ct_coords = List(Float)
#    surf_coords = List(Float)
#    snap_coords = List(Float)
    ct_coords = Tuple
    surf_coords = Tuple
    #snap_coords = Tuple
    snap_coords = Instance(np.ndarray)

    special_name = Str

    is_interpolation = Bool(False)
    grid_name = Str('unsorted')
    grid_transition_to = Str('')
    
    hemi = Str
    vertno = Int(-1)
    pial_coords = Instance(np.ndarray)

    plane_coords = Either(None, Tuple)
    #geom_coords = Either(None, Tuple)
    geom_coords = List(Int)

    name = Str
    corner = List

    roi_list = List(Str)

    strrepr = Property
    def _get_strrepr(self):
        if self.special_name != '':
            return self.special_name
        return str(self)

    #def __eq__(self, other):
    #    return np.all(self.snap_coords == other)

    def __str__(self):
        return 'Elec: %s %s'%(self.grid_name, self.ct_coords)
    def __repr__(self):
        return self.__str__()

    def astuple(self):
        return nparrayastuple(self.snap_coords)

    def asras(self):
        return tuple(self.surf_coords)

    def asct(self):
        return tuple(self.ct_coords)

def electrode_factory():
    return Electrode(special_name='Electrode for linear interpolation',
        is_interpolation=True)

def nparrayastuple(nparray):
    nparray = np.array(nparray)
    return (nparray[0], nparray[1], nparray[2])

class ElectrodeWindow(Handler):
    model = Any
    #we clumsily hold a reference to the model object to fire its events

    cur_grid = Str

    electrodes = List(Instance(Electrode))
    cur_sel = Instance(Electrode)
    selection_callback = Method
   
    selected_ixes = Any
    swap_action = Action(name='Swap', action='do_swap')

    previous_sel = Instance(Electrode)
    previous_color = Int

    distinct_prev_sel = Instance(Electrode)
    
    identify_action = Action(name='Identify ROIs', action='do_identify') 

    save_montage_action = Action(name='Save montage', action='do_montage')

    interpolate_action = Action(name='Linear interpolation',
        action='do_linear_interpolation')

    naming_convention = Enum('grid', 'reverse_grid', 'line')
    label_auto_action = Action(name='Label Automatically',
        action='do_label_automatically')

    name_stem = Str
    c1, c2, c3 = 3*(Instance(Electrode),)

    parcellation = Str

    #electrode_factory = Method

    traits_view = View(
        Item('electrodes',
            editor=TableEditor( columns = 
                [ObjectColumn(label='electrode',
                              editor=TextEditor(),
                              style='readonly',
                              editable=False,
                              name='strrepr'),

                 ObjectColumn(label='corner',
                              editor=CheckListEditor(
                                values=['','corner 1','corner 2',
                                    'corner 3']),
                              style='simple',
                              name='corner'),

                 ObjectColumn(label='geometry',
                              editor=CSVListEditor(),
                              #editor=TextEditor(),
                              #style='readonly',
                              #editable=False,
                              name='geom_coords'),
                              
                 ObjectColumn(label='channel name',
                              editor=TextEditor(),
                              name='name'),

                 ObjectColumn(label='ROIs',
                              editor=ListStrEditor(),
                              editable=False, 
                              name='roi_list'),
                 ],
                selected='cur_sel',
                deletable=True,
                row_factory=electrode_factory,
                ),
            show_label=False, height=350, width=700),

        VGroup(
            HGroup( 
                Label( 'Automatic labeling parameters' ),
                Item( 'name_stem' ),
                Item( 'naming_convention' ),
            ),
            HGroup(
                Label( 'Atlas for ROI identification (optional)' ),
                Item('parcellation'),
            ),
        ),

        resizable=True, kind='panel', title='modify electrodes',
        buttons=[OKButton, swap_action, label_auto_action,
            interpolate_action, save_montage_action]) 

    @on_trait_change('cur_sel')
    def selection_callback(self):
        if self.cur_sel is None:
            return

        if self.previous_sel is not None:
            self.model._new_glyph_color = self.previous_color
            self.model._single_glyph_to_recolor = self.previous_sel.asct()
            self.model._update_single_glyph_event = True

        self.previous_sel = self.cur_sel
        self.previous_color = self.model._colors.keys().index(self.cur_grid)

        selection_color = (self.model._colors.keys().index('selection'))

        self.model._new_glyph_color = selection_color
        self.model._single_glyph_to_recolor = self.cur_sel.asct()
        self.model._update_single_glyph_event = True

    def closed(self, is_ok, info):
        if self.previous_sel is not None:
            self.model._new_glyph_color = self.previous_color
            self.model._single_glyph_to_recolor = self.previous_sel.asct()
            self.model._update_single_glyph_event = True

    def do_swap(self, info):
        #if not len(self.selected_ixes) == 2:
        #    return
        if self.distinct_prev_sel == self.cur_sel:
            return
        elif None in (self.distinct_prev_sel, self.cur_sel):
            return

        #i,j = self.selected_ixes
        #e1 = self.electrodes[i]
        #e2 = self.electrodes[j]
        e1 = self.cur_sel
        e2 = self.distinct_prev_sel

        geom_swap = e1.geom_coords
        name_swap = e1.name

        e1.geom_coords = e2.geom_coords
        e1.name = e2.name

        e2.geom_coords = geom_swap
        e2.name = name_swap

    def do_label_automatically(self, info):
        #figure out c1, c2, c3
        c1,c2,c3 = 3*(None,)
        for e in self.electrodes:
            if len(e.corner) == 0:
                continue
            elif len(e.corner) > 1:
                error_dialog('Too many corners specified for single'
                    'electrode')
                return
    
            elif 'corner 1' in e.corner:
                c1 = e
            elif 'corner 2' in e.corner:
                c2 = e
            elif 'corner 3' in e.corner:
                c3 = e

        if c1 is None or c2 is None or c3 is None:
            error_dialog('Not all corners were specified')
            return
    
        cur_geom = self.model._grid_geom[self.cur_grid]
        if cur_geom=='user-defined' and self.naming_convention != 'line':
            from color_utils import mayavi2traits_color
            from utils import GeometryNameHolder, GeomGetterWindow
            nameholder = GeometryNameHolder(
                geometry=cur_geom,
                color=mayavi2traits_color(
                    self.model._colors[self.cur_grid]))
            geomgetterwindow = GeomGetterWindow(holder=nameholder)

            if geomgetterwindow.edit_traits().result:
                cur_geom = geomgetterwindow.geometry
            else:
                error_dialog("User did not specify any geometry")
                return

        import pipeline as pipe
        if self.naming_convention == 'line':
            pipe.fit_grid_to_line(self.electrodes, c1.asct(), c2.asct(),
                c3.asct(), cur_geom, delta=self.model.delta,
                rho_loose=self.model.rho_loose)
            #do actual labeling
            for elec in self.model._grids[self.cur_grid]:
                _,y = elec.geom_coords
                index = y+1
                elec.name = '%s%i'%(self.name_stem, index)

        else:
            pipe.fit_grid_to_plane(self.electrodes, c1.asct(), c2.asct(), 
                c3.asct(), cur_geom)

            #do actual labeling
            for elec in self.model._grids[self.cur_grid]:
                x,y = elec.geom_coords
                if self.first_axis=='standard':
                    #index = y*np.max(cur_geom) + x + 1
                    index = x*np.min(cur_geom) + y + 1
                else:
                    #index = x*np.min(cur_geom) + y + 1
                    index = y*np.max(cur_geom) + x + 1
                
                elec.name = '%s%i'%(self.name_stem, index)

    def do_linear_interpolation(self, info):
        if self.cur_sel is None:
            return
        elif self.cur_sel.special_name == '':
            return
        
        if len(self.cur_sel.geom_coords) == 0:
            error_dialog("Specify geom_coords before linear interpolation")
            return

        x,y = self.cur_sel.geom_coords

        x_low = self._find_closest_neighbor(self.cur_sel, 'x', '-')
        x_hi = self._find_closest_neighbor(self.cur_sel, 'x', '+')
        y_low = self._find_closest_neighbor(self.cur_sel, 'y', '-')
        y_hi = self._find_closest_neighbor(self.cur_sel, 'y', '+')

        loc = None

        #handle simplest case of electrode directly in between others
        if x_low is not None and x_hi is not None:
            xl = x_low.geom_coords[0]
            xh = x_hi.geom_coords[0]
            ratio = (x - xl) / (xh - xl)
        
            loc = np.array(x_low.surf_coords) + (np.array(x_hi.surf_coords)-
                np.array(x_low.surf_coords))*ratio

        elif y_low is not None and y_hi is not None:
            yl = y_low.geom_coords[1]
            yh = y_hi.geom_coords[1]
            ratio = (y - yl) / (yh - yl)
        
            loc = np.array(y_low.surf_coords) + (np.array(y_hi.surf_coords)-
                np.array(y_low.surf_coords))*ratio

        #handle poorer case of electrode on end of line
        if x_low is not None and loc is None:
            x_lower = self._find_closest_neighbor(x_low, 'x', '-')
            xl = x_low.geom_coords[0]
            xll = x_lower.geom_coords[0]
            if xl == xll+1:
                loc = 2*np.array(x_low.surf_coords) - np.array(
                    x_lower.surf_coords)

        if x_hi is not None and loc is None:
            x_higher = self._find_closest_neighbor(x_hi, 'x', '+')
            xh = x_hi.geom_coords[0]
            xhh = x_higher.geom_coords[0]
            if xh == xhh-1:
                loc = 2*np.array(x_hi.surf_coords) - np.array(
                    x_higher.surf_coords)

        import pdb
        pdb.set_trace()

        if y_low is not None and loc is None:
            y_lower = self._find_closest_neighbor(y_low, 'y', '-')
            yl = y_low.geom_coords[1]
            yll = y_lower.geom_coords[1]
            if yl == yll+1:
                loc = 2*np.array(y_low.surf_coords) - np.array(
                    y_lower.surf_coords)
        
        if y_hi is not None and loc is None:
            y_higher = self._find_closest_neighbor(y_hi, 'y', '+')
            yh = y_hi.geom_coords[0]
            yhh = y_higher.geom_coords[0]
            if yh == yhh-1:
                loc = 2*np.array(y_hi.surf_coords) - np.array(
                    y_higher.surf_coords)
    
        if loc is not None:
            self.cur_sel.surf_coords = tuple(loc)
            self.cur_sel.special_name = 'Linearly interpolated electrode'
        else:
            error_dialog('No line for simple linear interpolation\n'
                'Better algorithm needed')
            
    def _find_closest_neighbor(self, cur_elec, axis, direction): 
        x,y = cur_elec.geom_coords

        if direction=='+':
            new_ix = np.inf
        else:
            new_ix = -np.inf
        new_e = None

        for e in self.electrodes:
            if len(e.geom_coords) == 0:
                continue

            ex,ey = e.geom_coords
            
            if axis=='x' and direction=='+':
                if ex < new_ix and ex > x and ey == y:
                    new_e = e
                    new_ix = ex
            if axis=='x' and direction=='-':
                if ex > new_ix and ex < x and ey == y:
                    new_e = e
                    new_ix = ex
            if axis=='y' and direction=='+':
                if ey < new_ix and ey > y and ex == x:
                    new_e = e
                    new_ix = ey
            if axis=='y' and direction=='-':
                if ey > new_ix and ey < y and ex == x:
                    new_e = e
                    new_ix = ey

        return new_e

    def do_montage(self, info):
        pass
