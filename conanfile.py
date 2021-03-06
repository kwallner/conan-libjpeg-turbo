import os
from conans import ConanFile, CMake, tools

class LibJpegTurboConan(ConanFile):
    name = "libjpeg-turbo"
    version = "1.5.3"
    ZIP_FOLDER_NAME = "%s-%s" % (name, version)
    generators = "cmake", "txt"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "SSE": [True, False]}
    default_options = "shared=False", "fPIC=True", "SSE=True"
    exports = "CMakeLists.txt"
    url="http://github.com/kwallner/conan-libjpeg-turbo"
    license="https://github.com/libjpeg-turbo/libjpeg-turbo/blob/%s/LICENSE.txt" % version
    
    def config(self):
        try: # Try catch can be removed when conan 0.8 is released
            del self.settings.compiler.libcxx 
        except: 
            pass
        
        if self.settings.os == "Windows":
            self.requires.add("nasm/2.12.02@lasote/stable", "private")
       
    def source(self):
        zip_name = "%s.tar.gz" % self.ZIP_FOLDER_NAME
        tools.download("http://downloads.sourceforge.net/project/libjpeg-turbo/%s/%s" % (self.version, zip_name), zip_name, verify=False)
        tools.unzip(zip_name)
        os.unlink(zip_name)
        
        if self.settings.os == "Linux" or self.settings.os == "Macos":
            pass
        else:
            conan_magic_lines = '''project(libjpeg-turbo)
cmake_minimum_required(VERSION 2.8.11)
include(../conanbuildinfo.cmake)
CONAN_BASIC_SETUP()
'''
            tools.replace_in_file("%s/CMakeLists.txt" % self.ZIP_FOLDER_NAME, "cmake_minimum_required(VERSION 2.8.11)", conan_magic_lines)
            tools.replace_in_file("%s/CMakeLists.txt" % self.ZIP_FOLDER_NAME, "project(libjpeg-turbo C)", "")
            
            # Don't mess with runtime conan already set
            tools.replace_in_file("%s/CMakeLists.txt" % self.ZIP_FOLDER_NAME, 'string(REGEX REPLACE "/MD" "/MT" ${var} "${${var}}")', "")
            tools.replace_in_file("%s/sharedlib/CMakeLists.txt" % self.ZIP_FOLDER_NAME, 'string(REGEX REPLACE "/MT" "/MD" ${var} "${${var}}")', "")

            # Fix install
            tools.replace_in_file("%s/CMakeLists.txt" % self.ZIP_FOLDER_NAME, 'install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/', 'install(PROGRAMS ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/')
            
    def build(self):
        """ Define your project building. You decide the way of building it
            to reuse it later in any other project.
        """
        if self.settings.os == "Linux" or self.settings.os == "Macos":

            fpic_flag= "-fPIC" if self.options.fPIC else "";

            # Skip this ... is it needed?
            #self.run("cd %s && autoreconf -fiv" % self.ZIP_FOLDER_NAME)
            
            config_options = ""
            if self.settings.arch == "x86":
                if self.settings.os == "Linux":
                    config_options = "--host i686-pc-linux-gnu CFLAGS='-O3 -m32 %s' LDFLAGS='-m32 %s'" % (fpic_flag, fpic_flag)
                else:
                    config_options = "--host i686-apple-darwin CFLAGS='-O3 -m32 %s' LDFLAGS='-m32 %s'" % (fpic_flag, fpic_flag)
            else:
                config_options = "CFLAGS='-O3 %s' LDFLAGS='%s'" % (fpic_flag, fpic_flag)

            if self.settings.os == "Macos":
                old_str = '-install_name \$rpath/\$soname'
                new_str = '-install_name \$soname'
                replace_in_file("./%s/configure" % self.ZIP_FOLDER_NAME, old_str, new_str)

            self.run("cd %s && ./configure %s" % (self.ZIP_FOLDER_NAME, config_options))
            self.run("cd %s && make" % (self.ZIP_FOLDER_NAME))
        else:
            cmake = CMake(self)
            
            if self.options.shared:
                cmake.definitions["ENABLE_STATIC"] = "0"
                cmake.definitions["ENABLE_SHARED"] = "1"
            else:
                cmake.definitions["ENABLE_STATIC"] = "1"
                cmake.definitions["ENABLE_SHARED"] = "0"
            
            cmake.definitions["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.shared or self.options.fPIC
            cmake.definitions["WITH_SIMD"] = "1" if self.options.SSE else "0"
            
            cmake.configure(source_dir="%s" % self.ZIP_FOLDER_NAME)
            cmake.build()            
            cmake.install()
                
    def package(self):
        """ Define your conan structure: headers, libs, bins and data. After building your
            project, this method is called to create a defined structure:
        """
        # Copying headers ... also for cmake as some are missing
        self.copy("*.h", "include", "%s" % (self.ZIP_FOLDER_NAME), keep_path=False)
        self.copy("jconfig.h", "include", ".", keep_path=False)
        self.copy("jconfigint.h", "include", ".", keep_path=False)
            
        # Copying static and dynamic libs
        if self.settings.os != "Windows":
            if self.options.shared:
                if self.settings.os == "Macos":
                    self.copy(pattern="*.dylib", dst="lib", keep_path=False)
                else:
                    self.copy(pattern="*.so*", dst="lib", src=self.ZIP_FOLDER_NAME, keep_path=False)
            else:
                self.copy(pattern="*.a", dst="lib", src=self.ZIP_FOLDER_NAME, keep_path=False)

    def package_info(self):
        # Naming scheme is strange: Only Mingw is using the static extension
        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio" and not self.options.shared:
            self.cpp_info.libs = ['jpeg-static', 'turbojpeg-static']
        else:
            self.cpp_info.libs = ['jpeg', 'turbojpeg']
