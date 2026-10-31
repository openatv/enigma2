#pragma once

#include <locale.h>

// gles_version.h
// Runtime GLES version singleton.
// Set exactly once by gEGLDC::initEGL() after the EGL context is created.
// All shader and atlas files read isGLES3() to select their code paths.

namespace gles
{
    // VC5 parses GLSL decimal constants using the calling thread's locale.
    // Python may have selected a comma-decimal locale before lazy compilation.
    // Keep shader creation independent of the UI locale without setlocale().
    class ShaderLocale
    {
        locale_t m_locale;
        locale_t m_previous;
    public:
        ShaderLocale() : m_locale(newlocale(LC_NUMERIC_MASK, "C", nullptr)), m_previous(nullptr)
        {
            if (m_locale) {
                m_previous = uselocale(m_locale);
                if (!m_previous) {
                    freelocale(m_locale);
                    m_locale = nullptr;
                }
            }
        }
        ~ShaderLocale()
        {
            if (m_locale) {
                uselocale(m_previous);
                freelocale(m_locale);
            }
        }
        ShaderLocale(const ShaderLocale&) = delete;
        ShaderLocale& operator=(const ShaderLocale&) = delete;
        bool valid() const { return m_locale != nullptr; }
    };

    // 2 = OpenGL ES 2.0, 3 = OpenGL ES 3.0
    // 0 means not yet initialised (context not created).
    extern int version;

    inline bool isGLES3() { return version >= 3; }
}
