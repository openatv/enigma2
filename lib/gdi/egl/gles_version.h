#pragma once

// gles_version.h
// Runtime GLES version singleton.
// Set exactly once by gEGLDC::initEGL() after the EGL context is created.
// All shader and atlas files read isGLES3() to select their code paths.

namespace gles
{
    // 2 = OpenGL ES 2.0, 3 = OpenGL ES 3.0
    // 0 means not yet initialised (context not created).
    extern int version;

    inline bool isGLES3() { return version >= 3; }
}
