from __future__ import division

import numpy as np

from traits.api import (HasTraits, List, Instance, Any, Enum, Tuple, Float,
    Property, Bool, on_trait_change, Dict, DelegatesTo, Str, Instance)
from traitsui.api import (View, Item, HGroup, VGroup, Group, NullEditor,
    InstanceEditor, CSVListEditor, Spring)

from enable.component_editor import ComponentEditor
from chaco.api import Plot, ArrayPlotData
from chaco.api import bone as bone_cmap
from chaco.api import RdBu as rdbu_cmap
from chaco.api import reverse as reverse_cmap
from chaco.tools.api import SelectTool

import nibabel as nib

from geometry import truncate, apply_affine, get_vox2rasxfm

reorient_orig2std_tkr_mat = np.array(((1, 0, 0, 0),
                                      (0, 0, -1, 0),
                                      (0, 1, 0, 0),
                                      (0, 0, 0, 1)))

ras2mni_mat = np.array(((1, 0, 0, 128),
                        (0, 0, -1, 128),
                        (0, 1, 0, 128),
                        (0, 0, 0, 1)))

def get_orig2std(orig):
    '''
    Given an orig file, get the transformation from the orig to ras2mni.
    '''
    vox2ras = get_vox2rasxfm(orig)
    bx, by, bz = vox2ras[0:3,3]

    reorient_orig2std_mat = np.array(((1, 0, 0, bx-128),
                                      (0, 0, -1, by+128), 
                                      (0, 1, 0, bz-128),
                                      (0, 0, 0, 1)))

    return reorient_orig2std_mat

class Click2DPanelTool(SelectTool):
    
    panel2d = Any #Instance(TwoDimensionalPanel)
    panel_id = Enum('xy','xz','yz')

    def __init__(self, panel2d, panel_id):
        self.panel2d = panel2d
        self.panel_id = panel_id

    def normal_left_down(self, event):
        x,y,z = self.panel2d.cursor            

        #if the panel is not in the image (e.g. click on the axis), ignore it

        #remember event.x and event.y are in space of pixels

        if self.panel_id == 'xy':
            mx, my = self.panel2d.xy_plane.map_data((event.x, event.y))
            if x == mx and y == my:
                return
            self.panel2d.move_cursor(mx, my, z)

        elif self.panel_id == 'xz':
            mx, mz = self.panel2d.xz_plane.map_data((event.x, event.y))
            if x == mx and z == mz:
                return
            self.panel2d.move_cursor(mx, y, mz)

        elif self.panel_id == 'yz':
            my, mz = self.panel2d.yz_plane.map_data((event.x, event.y))
            if y == my and z == mz:
                return
            self.panel2d.move_cursor(x, my, mz)

        else:
            raise NotImplementedError('FailFish')

    def normal_right_down(self, event):
        x,y,z = self.panel2d.cursor
        px,py,pz = self.panel2d.pins[self.panel2d.current_pin]

        if self.panel_id == 'xy':
            mx, my = self.panel2d.xy_plane.map_data((event.x, event.y))
            if px == mx and py == my:
                return
            self.panel2d.drop_pin(mx, my, z, name=self.panel2d.current_pin)

        elif self.panel_id == 'xz':
            mx, mz = self.panel2d.xy_plane.map_data((event.x, event.y))
            if px == mx and pz == mz:
                return
            self.panel2d.drop_pin(mx, y, mz, name=self.panel2d.current_pin)

        elif self.panel_id == 'yz':
            my, mz = self.panel2d.yz_plane.map_data((event.x, event.y))
            if py == my and pz == mz:
                return
            self.panel2d.drop_pin(x, my, mz, name=self.panel2d.current_pin)

        else:
            raise NotImplementedError('BabyRage')

    def normal_mouse_move(self, event):
        x,y,z = self.panel2d.cursor    

        if self.panel_id == 'xy':
            mx, my = self.panel2d.xy_plane.map_data((event.x, event.y))
            self.panel2d.move_mouse(mx, my, z) 

        elif self.panel_id == 'xz':
            mx, mz = self.panel2d.xy_plane.map_data((event.x, event.y))
            self.panel2d.move_mouse(mx, y, mz)

        elif self.panel_id == 'yz':
            my, mz = self.panel2d.yz_plane.map_data((event.x, event.y))
            self.panel2d.move_mouse(x, my, mz)

        else:
            raise NotImplementedError('DansGame')

class NullInstanceHolder(HasTraits):
    name = Str
    traits_view = View( Spring() )

class InfoPanel(HasTraits):
    cursor = Property(Tuple)
    cursor_ras = Property(Tuple)
    cursor_tkr = Property(Tuple)
    cursor_intensity = Float

    mouse = Tuple((0.,0.,0.))
    mouse_ras = Tuple((0.,0.,0.))
    mouse_tkr = Tuple((0.,0.,0.))
    mouse_intensity = Float

    cursor_csvlist = List(Float)
    cursor_ras_csvlist = List(Float)
    cursor_tkr_csvlist = List(Float)

    pin_tolerance = Float(7.5)
    currently_showing_list = List(Instance(NullInstanceHolder))
    currently_showing = Instance(NullInstanceHolder)

    traits_view = View(
        VGroup(
            Item('currently_showing', 
                editor=InstanceEditor(name='currently_showing_list'),
                style='custom'),
            Spring(),
            Item(name='cursor_csvlist', style='text', label='cursor',
                editor=CSVListEditor(enter_set=True, auto_set=False)),
            Item(name='cursor_ras_csvlist', style='text', label='cursor RAS',
                editor=CSVListEditor(enter_set=True, auto_set=False)),
            Item(name='cursor_tkr_csvlist', style='text', label='cursor tkr',
                editor=CSVListEditor(enter_set=True, auto_set=False)),
            Item(name='cursor_intensity', style='readonly',
                label='cursor intensity'),
            Item(name='mouse', style='readonly', label='mouse'),
            Item(name='mouse_ras', style='readonly', label='mouse RAS'),
            Item(name='mouse_tkr', style='readonly', label='mouse tkr'),
            Item(name='mouse_intensity', style='readonly',
                label='mouse intensity'),
            Spring(),
            Item('pin_tolerance'),
        ),
        title='ilumbumbargu',
    )

    def _get_cursor(self):
        return tuple(self.cursor_csvlist)
    def _set_cursor(self, newval):
        self.cursor_csvlist = list(newval)
    def _get_cursor_ras(self):
        return tuple(self.cursor_ras_csvlist)
    def _set_cursor_ras(self, newval):
        self.cursor_ras_csvlist = list(newval)
    def _get_cursor_tkr(self):
        return tuple(self.cursor_tkr_csvlist)
    def _set_cursor_tkr(self, newval):
        self.cursor_tkr_csvlist = list(newval)

class TwoDimensionalPanel(HasTraits):
    images = Dict # Str -> Tuple(imgd, affine, tkr_affine)

    current_image = Any # np.ndarray XxYxZ
    current_affine = Any
    current_tkr_affine = Any

    xy_plane = Instance(Plot)
    xz_plane = Instance(Plot)
    yz_plane = Instance(Plot)
    
    pins = Dict # Str -> 3-Tuple
    pin_tolerance = DelegatesTo('info_panel')

    current_pin = Str('pin')

    info_panel = Instance(InfoPanel, ())

    currently_showing_list = DelegatesTo('info_panel')
    currently_showing = DelegatesTo('info_panel')

    #later we will rename cursor to "coord"

    cursor = Tuple # 3-tuple

    null = Any # None

    _finished_plotting = Bool(False)

    traits_view = View(
        Group(
        HGroup(
            Item(name='xz_plane', editor=ComponentEditor(),
                height=400, width=400, show_label=False, resizable=True),
            Item(name='yz_plane', editor=ComponentEditor(),
                height=400, width=400, show_label=False, resizable=True),
        ),
        HGroup(
            Item(name='xy_plane', editor=ComponentEditor(),
                height=400, width=400, show_label=False, resizable=True),
            Item(name='info_panel', 
                    editor=InstanceEditor(), 
                style='custom',
            #Item(name='null', editor=NullEditor(),
                height=400, width=400, show_label=False, resizable=True),
        ),
        ),
        title='Contact 867-5309 for blobfish sales',
    )

    def map_cursor(self, cursor, affine, invert=False):
        x,y,z = cursor
        aff_to_use = np.linalg.inv(affine) if invert else affine
        mcursor, = apply_affine([cursor], aff_to_use)
        return tuple(map(lambda x: truncate(x, 2), mcursor))

    def cut_data(self, data, mcursor):
        xm,ym,zm = [int(np.round(c)) for c in mcursor]
        #xm, ym, zm = mcursor
        #yz_cut = np.rot90(data[xm,:,:].T)
        #xz_cut = np.rot90(data[:,ym,:].T)
        #xy_cut = np.rot90(data[:,:,zm].T)
        yz_cut = data[xm,:,:].T
        xz_cut = data[:,ym,:].T
        xy_cut = data[:,:,zm].T
        return xy_cut, xz_cut, yz_cut

    def load_img(self, imgf, reorient2std=False, image_name=None):
        self._finished_plotting = False

        img = nib.load(imgf)

        self.current_affine = aff = np.dot(
            get_orig2std(imgf) if reorient2std else np.eye(4),
            img.get_affine())
        self.current_tkr_affine = tkr_aff = np.dot(
            reorient_orig2std_tkr_mat if reorient2std else np.eye(4),
            get_vox2rasxfm(imgf, stem='vox2ras-tkr'))

        #from nilearn.image.resampling import reorder_img

        #img = reorder_img(uimg, resample='continuous')

        xsz, ysz, zsz = img.shape

        #print 'image coordinate transform', img.get_affine()

        imgd = img.get_data()
        if reorient2std:
            imgd = np.swapaxes(imgd, 1, 2)[:,:,::-1]

        print 'image size', imgd.shape

        self.current_image = imgd

        if image_name is None:
            from utils import gensym
            image_name = 'image%s'%gensym()

        self.images[image_name] = (imgd, aff, tkr_aff)
        self.currently_showing_list.append(
            NullInstanceHolder(name=image_name))

        self.cursor = x,y,z = tuple(np.array(imgd.shape) // 2)

        xy_cut, xz_cut, yz_cut = self.cut_data(imgd, self.cursor)

        print xy_cut.shape, xz_cut.shape, yz_cut.shape

        xy_plotdata = ArrayPlotData()
        xy_plotdata.set_data('imagedata', xy_cut)
        xy_plotdata.set_data('cursor_x', np.array((x,)))
        xy_plotdata.set_data('cursor_y', np.array((y,)))

        xz_plotdata = ArrayPlotData()
        xz_plotdata.set_data('imagedata', xz_cut)
        xz_plotdata.set_data('cursor_x', np.array((x,)))
        xz_plotdata.set_data('cursor_z', np.array((z,)))

        yz_plotdata = ArrayPlotData()
        yz_plotdata.set_data('imagedata', yz_cut)
        yz_plotdata.set_data('cursor_y', np.array((y,)))
        yz_plotdata.set_data('cursor_z', np.array((z,)))

        self.xy_plane = Plot(xy_plotdata, bgcolor='black',
            aspect_ratio=xsz/ysz)
        self.xz_plane = Plot(xz_plotdata, bgcolor='black',
            aspect_ratio=xsz/zsz)
        self.yz_plane = Plot(yz_plotdata, bgcolor='black',
            aspect_ratio=ysz/zsz)

        self.xy_plane.img_plot('imagedata',name='brain',colormap=bone_cmap)
        self.xz_plane.img_plot('imagedata',name='brain',colormap=bone_cmap)
        self.yz_plane.img_plot('imagedata',name='brain',colormap=bone_cmap)

        #self.xz_plane.y_mapper.range.high = 512

        self.xy_plane.plot(('cursor_x','cursor_y'), type='scatter', 
            color='red', marker='plus', size=3, name='cursor')
        self.xz_plane.plot(('cursor_x','cursor_z'), type='scatter',
            color='red', marker='plus', size=3, name='cursor')
        self.yz_plane.plot(('cursor_y','cursor_z'), type='scatter',
            color='red', marker='plus', size=3, name='cursor')

        self.xy_plane.tools.append(Click2DPanelTool(self, 'xy'))
        self.xz_plane.tools.append(Click2DPanelTool(self, 'xz'))
        self.yz_plane.tools.append(Click2DPanelTool(self, 'yz'))

        #from PyQt4.QtCore import pyqtRemoveInputHook
        #import pdb
        #pyqtRemoveInputHook()
        #pdb.set_trace()

        self.info_panel.cursor = self.cursor
        self.info_panel.cursor_ras = self.map_cursor(self.cursor, aff)
        self.info_panel.cursor_tkr = self.map_cursor(self.cursor,
            self.current_tkr_affine)
        self.info_panel.cursor_intensity = self.current_image[x,y,z]

        self._finished_plotting = True

    @on_trait_change('currently_showing')
    def switch_image_listen(self):
        self.switch_image(self.currently_showing.name)

    def switch_image(self, image_name, xyz=None):
        self.current_image, self.current_affine, self.current_tkr_affine = (
            self.images[image_name])

        if xyz is None:
            xyz = tuple(np.array(self.current_image.shape) // 2)
        x,y,z = xyz

        self.move_cursor(x,y,z)
        #make sure coordinate system is correct, currently it isnt right
        #and needs to be able to dynamically resize the grid
        #this will probably be done most easily by destroying and rebuilding it

    def cursor_outside_image_dimensions(self, cursor, image=None):
        if image is None:
            image = self.current_image

        x, y, z = cursor

        x_sz, y_sz, z_sz = image.shape

        if not 0 <= x < x_sz:
            return True
        if not 0 <= y < y_sz:
            return True
        if not 0 <= z < z_sz:
            return True
        
        return False

    def move_cursor(self, x, y, z, suppress_cursor=False, suppress_ras=False,
            suppress_tkr=False):

        #it doesnt seem necessary for the instance variable cursor to exist
        #at all but this code isn't broken
        cursor = x,y,z

        if self.cursor_outside_image_dimensions(cursor):
            return

        self.cursor = cursor

        xy_cut, xz_cut, yz_cut = self.cut_data(self.current_image, self.cursor)

        print 'clicked on point %.2f %.2f %.2f'%(x,y,z)

        self.xy_plane.data.set_data('imagedata', xy_cut)
        self.xz_plane.data.set_data('imagedata', xz_cut)
        self.yz_plane.data.set_data('imagedata', yz_cut)

        self.xy_plane.data.set_data('cursor_x', np.array((x,)))
        self.xy_plane.data.set_data('cursor_y', np.array((y,)))

        self.xz_plane.data.set_data('cursor_x', np.array((x,)))
        self.xz_plane.data.set_data('cursor_z', np.array((z,)))

        self.yz_plane.data.set_data('cursor_y', np.array((y,)))
        self.yz_plane.data.set_data('cursor_z', np.array((z,)))

        if not suppress_cursor:
            self.info_panel.cursor = tuple(
                map(lambda x:truncate(x, 2), self.cursor))
        if not suppress_ras:
            self.info_panel.cursor_ras = self.map_cursor(self.cursor,
                self.current_affine)
        if not suppress_tkr:
            self.info_panel.cursor_tkr = self.map_cursor(self.cursor,
                self.current_tkr_affine)
        self.info_panel.cursor_intensity = truncate(self.current_image[x,y,z],3)

        for pin in self.pins:
            px, py, pz = self.pins[pin]
            self.drop_pin(px,py,pz, name=pin)
            #self.draw_pin(pin)

    def redraw(self):
        self.xz_plane.request_redraw()
        self.yz_plane.request_redraw()
        self.xy_plane.request_redraw()

    def drop_pin(self, x, y, z, name='pin', color='yellow'):
        pin = (x,y,z)
        cx, cy, cz = self.cursor

        tolerance = self.pin_tolerance

        self.xy_plane.data.set_data('%s_x'%name, 
            np.array((x,) if np.abs(z - cz) < tolerance else ()))
        self.xy_plane.data.set_data('%s_y'%name, 
            np.array((y,) if np.abs(z - cz) < tolerance else ()))
        
        self.xz_plane.data.set_data('%s_x'%name, 
            np.array((x,) if np.abs(y - cy) < tolerance else ()))
        self.xz_plane.data.set_data('%s_z'%name, 
            np.array((z,) if np.abs(y - cy) < tolerance else ()))
    
        #currently the pin doesn't show up at all because the electrode
        #doesn't match the immediate starting coordinates

        #move_cursor also needs to check to enable pins, maybe there is a
        #simpler way of doing it

        #i think we should hold off on finishing this for at least a week 
        #or two
        self.yz_plane.data.set_data('%s_y'%name, 
            np.array((y,) if np.abs(x - cx) < tolerance else ()))
        self.yz_plane.data.set_data('%s_z'%name, 
            np.array((z,) if np.abs(x - cx) < tolerance else ()))

        #if name not in self.xy_plane.plots:
        if name not in self.pins:
            self.xy_plane.plot(('%s_x'%name,'%s_y'%name), type='scatter', 
                color=color, marker='dot', size=4, name=name)
            self.xz_plane.plot(('%s_x'%name,'%s_z'%name), type='scatter',
                color=color, marker='dot', size=4, name=name)
            self.yz_plane.plot(('%s_y'%name,'%s_z'%name), type='scatter',
                color=color, marker='dot', size=4, name=name)

            self.redraw()

        self.pins[name] = (x,y,z)

#    def draw_pin(self, name, tolerance=0.75):
#        x, y, z = self.pins[name]
#        cx, cy, cz = self.cursor
#
#        self.xy_plane.data.set_data('%s_x'%name, 
#            np.array((x,) if np.abs(z - cz) < tolerance else ()))
#        self.xy_plane.data.set_data('%s_y'%name, 
#            np.array((y,) if np.abs(z - cz) < tolerance else ()))
#        
#        self.xz_plane.data.set_data('%s_x'%name, 
#            np.array((x,) if np.abs(y - cy) < tolerance else ()))
#        self.xz_plane.data.set_data('%s_z'%name, 
#            np.array((z,) if np.abs(y - cy) < tolerance else ()))
#
#        self.yz_plane.data.set_data('%s_y'%name, 
#            np.array((y,) if np.abs(x - cx) < tolerance else ()))
#        self.yz_plane.data.set_data('%s_z'%name, 
#            np.array((z,) if np.abs(x - cx) < tolerance else ()))

    def move_mouse(self, x, y, z):
        mouse = (x,y,z)

        if self.cursor_outside_image_dimensions(mouse):
            return

        self.info_panel.mouse = tuple(map(lambda x:truncate(x, 2), mouse))
        self.info_panel.mouse_ras = self.map_cursor(mouse,
            self.current_affine)
        self.info_panel.mouse_tkr = self.map_cursor(mouse, 
            self.current_tkr_affine)
        self.info_panel.mouse_intensity = truncate(self.current_image[x,y,z], 3)

    #because these calls all call map_cursor, which changes the listener
    #variables they end up infinite looping.

    #to solve this we manage _finished_plotting manually
    #so that move_cursor is only called once when any listener is triggered
    @on_trait_change('info_panel:cursor_csvlist')
    def _listen_cursor(self):
        if self._finished_plotting:
            self._finished_plotting = False
            x,y,z = self.info_panel.cursor
            self.move_cursor(x,y,z, suppress_cursor=True)
            self._finished_plotting = True

    @on_trait_change('info_panel:cursor_ras_csvlist')
    def _listen_cursor_ras(self):
        if self._finished_plotting:
            self._finished_plotting = False
            x,y,z = self.map_cursor(self.info_panel.cursor_ras,
                self.current_affine, invert=True)
            self.move_cursor(x,y,z, suppress_ras=True)
            self._finished_plotting = True

    @on_trait_change('info_panel:cursor_tkr_csvlist')
    def _listen_cursor_tkr(self):
        if self._finished_plotting:
            self._finished_plotting = False
            x,y,z = self.map_cursor(self.info_panel.cursor_tkr,
                self.current_tkr_affine, invert=True)
            self.move_cursor(x,y,z, suppress_tkr=True)
            self._finished_plotting = True
