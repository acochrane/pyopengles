#
# Copyright (c) 2012 Peter de Rivaz
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted.
#
# Raspberry Pi 3d demo using OpenGLES 2.0 via Python
#
# Version 0.1 (Draws a rectangle using vertex and fragment shaders)

import ctypes
import time
# Pick up our constants extracted from the header files with prepare_constants.py
from egl import *
from gl2 import *
from gl2ext import *

# Define verbose=True to get debug messages
verbose = True

# Define some extra constants that the automatic extraction misses
EGL_DEFAULT_DISPLAY = 0
EGL_NO_CONTEXT = 0
EGL_NO_DISPLAY = 0
EGL_NO_SURFACE = 0
DISPMANX_PROTECTION_NONE = 0

# Open the libraries
bcm = ctypes.CDLL('libbcm_host.so')
opengles = ctypes.CDLL('libGLESv2.so')
openegl = ctypes.CDLL('libEGL.so')

eglint = ctypes.c_int

def eglints(L):
    """Converts a tuple to an array of eglints (would a pointer return be better?)"""
    return (eglint*len(L))(*L)

eglfloat = ctypes.c_float

def eglfloats(L):
    return (eglfloat*len(L))(*L)
                
def check(e):
    """Checks that error is zero"""
    if e==0: return
    if verbose:
        print 'Error code',hex(e&0xffffffff)
    raise ValueError

class EGL(object):

    def __init__(self):
        """Opens up the OpenGL library and prepares a window for display"""
        b = bcm.bcm_host_init()
        assert b==0
        self.display = openegl.eglGetDisplay(EGL_DEFAULT_DISPLAY)
        assert self.display
        r = openegl.eglInitialize(self.display,0,0)
        assert r
        attribute_list = eglints(     (EGL_RED_SIZE, 8,
                                      EGL_GREEN_SIZE, 8,
                                      EGL_BLUE_SIZE, 8,
                                      EGL_ALPHA_SIZE, 8,
                                      EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
                                      EGL_NONE) )
        numconfig = eglint()
        config = ctypes.c_void_p()
        r = openegl.eglChooseConfig(self.display,
                                     ctypes.byref(attribute_list),
                                     ctypes.byref(config), 1,
                                     ctypes.byref(numconfig));
        assert r
        r = openegl.eglBindAPI(EGL_OPENGL_ES_API)
        assert r
        if verbose:
            print 'numconfig=',numconfig
        context_attribs = eglints( (EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE) )
        self.context = openegl.eglCreateContext(self.display, config,
                                        EGL_NO_CONTEXT,
                                        ctypes.byref(context_attribs))
        assert self.context != EGL_NO_CONTEXT
        width = eglint()
        height = eglint()
        s = bcm.graphics_get_display_size(0,ctypes.byref(width),ctypes.byref(height))
        self.width = width
        self.height = height
        assert s>=0
        dispman_display = bcm.vc_dispmanx_display_open(0)
        dispman_update = bcm.vc_dispmanx_update_start( 0 )
        dst_rect = eglints( (0,0,width.value,height.value) )
        src_rect = eglints( (0,0,width.value<<16, height.value<<16) )
        assert dispman_update
        assert dispman_display
        dispman_element = bcm.vc_dispmanx_element_add ( dispman_update, dispman_display,
                                  0, ctypes.byref(dst_rect), 0,
                                  ctypes.byref(src_rect),
                                  DISPMANX_PROTECTION_NONE,
                                  0 , 0, 0)
        bcm.vc_dispmanx_update_submit_sync( dispman_update )
        nativewindow = eglints((dispman_element,width,height));
        nw_p = ctypes.pointer(nativewindow)
        self.nw_p = nw_p
        self.surface = openegl.eglCreateWindowSurface( self.display, config, nw_p, 0)
        assert self.surface != EGL_NO_SURFACE
        r = openegl.eglMakeCurrent(self.display, self.surface, self.surface, self.context)
        assert r

class demo():

    def showlog(self,shader):
        """Prints the compile log for a shader"""
        N=1024
        log=(ctypes.c_char*N)()
        loglen=ctypes.c_int()
        opengles.glGetShaderInfoLog(shader,N,ctypes.byref(loglen),ctypes.byref(log))
        print log.value

    def showprogramlog(self,shader):
        """Prints the compile log for a shader"""
        N=1024
        log=(ctypes.c_char*N)()
        loglen=ctypes.c_int()
        opengles.glGetProgramInfoLog(shader,N,ctypes.byref(loglen),ctypes.byref(log))
        print log.value
            
    def __init__(self):
        self.vertex_data = eglfloats((0.0,0.0,0.5,1.0,
                         1.0,0.0,0.5,1.0,
                         1.0,1.0,0.5,1.0,
                         0.0,1.0,0.5,1.0))
        self.vshader_source = ctypes.c_char_p(
              "attribute vec4 vertex;"
              "void main(void) {"
              "  vec4 pos = vertex;"
              "  pos.xy*=0.3;"
              "  gl_Position = pos;"
              "}")
      
        self.fshader_source = ctypes.c_char_p(
              "uniform vec4 color;"
              "void main(void) {"
              "   gl_FragColor = color;"
              "}")

        vshader = opengles.glCreateShader(GL_VERTEX_SHADER);
        opengles.glShaderSource(vshader, 1, ctypes.byref(self.vshader_source), 0)
        opengles.glCompileShader(vshader);

        if verbose:
            self.showlog(vshader)
            
        fshader = opengles.glCreateShader(GL_FRAGMENT_SHADER);
        opengles.glShaderSource(fshader, 1, ctypes.byref(self.fshader_source), 0);
        opengles.glCompileShader(fshader);

        if verbose:
            self.showlog(fshader)

        program = opengles.glCreateProgram();
        opengles.glAttachShader(program, vshader);
        opengles.glAttachShader(program, fshader);
        opengles.glLinkProgram(program);

        if verbose:
            self.showprogramlog(program)
            
        self.program = program
        self.unif_color = opengles.glGetUniformLocation(program, "color");
        self.attr_vertex = opengles.glGetAttribLocation(program, "vertex");
   
        opengles.glClearColor ( eglfloat(0.0), eglfloat(1.0), eglfloat(1.0), eglfloat(1.0) );
        
        self.buf=eglint()
        opengles.glGenBuffers(1,ctypes.byref(self.buf))

    def draw_triangles(self):
        opengles.glViewport ( 0, 0, egl.width, egl.height );
       
        opengles.glUseProgram ( self.program );

        opengles.glBindBuffer(GL_ARRAY_BUFFER, self.buf);
        opengles.glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(self.vertex_data),
                             ctypes.byref(self.vertex_data), GL_STATIC_DRAW);
        opengles.glVertexAttribPointer(self.attr_vertex, 4, GL_FLOAT, 0, 16, 0);
        opengles.glEnableVertexAttribArray(self.attr_vertex);
       
        opengles.glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
        #opengles.glClear(GL_COLOR_BUFFER_BIT);
        #opengles.glClear(GL_DEPTH_BUFFER_BIT);
        opengles.glUniform4f(self.unif_color, eglfloat(0.5), eglfloat(0.5), eglfloat(0.8), eglfloat(1.0));
        opengles.glDrawArrays ( GL_TRIANGLE_FAN, 0, 4 );
        opengles.glBindBuffer(GL_ARRAY_BUFFER, 0);

        openegl.eglSwapBuffers(egl.display, egl.surface);

        
def showerror():
    e=opengles.glGetError()
    print hex(e)
    
if __name__ == "__main__":
    egl = EGL()
    d = demo()
    d.draw_triangles()
    showerror()
        
    
