/// Some utilities for OpenGL
module gld.util;

/// Split the extension string returned by `gl.GetString(GL_EXTENSIONS)`
/// into D strings (one per extension).
string[] splitExtString(const(char)* str) {
    import std.array : split;
    import std.string : fromStringz;
    return fromStringz(str).idup.split();
}
