#!/usr/bin/env python3
import sys, os, subprocess

def die(m):
    print(m, file=sys.stderr)
    sys.exit(1)

def run(c):
    print(">", " ".join(c))
    subprocess.run(c, check=True)

def parse():
    if len(sys.argv) < 3:
        die("usage: python main.py <file.bybylang> --aot=<name> [--emit=js|wasm]")
    f = sys.argv[1]
    a, e = None, "js"
    for x in sys.argv[2:]:
        if x.startswith("--aot="):
            a = x.split("=", 1)[1]
        elif x.startswith("--emit="):
            e = x.split("=", 1)[1]
    if not f.endswith(".bybylang"):
        die("đuôi file phải là .bybylang")
    if not os.path.exists(f):
        die("không thấy " + f)
    if not a:
        a = os.path.splitext(os.path.basename(f))[0]
    if e not in ("js", "wasm"):
        die("--emit chỉ nhận js hoặc wasm")
    return f, a, e

def find_nim_include():
    try:
        r = subprocess.run(
            ["nim", "dump", "--libpath"],
            capture_output=True, text=True
        )
        path = r.stdout.strip()
        if os.path.exists(path):
            return path
    except:
        pass
    return os.path.expanduser("~/.choosenim/toolchains/nim-2.2.4/lib")

def main():
    f, a, e = parse()

    # 1. Biên dịch BybyLang -> Nim
    run(["bybylang", f, f"--aot={a}"])
    n = f"{a}.nim"
    if not os.path.exists(n):
        die("bybylang không tạo " + n)

    if e == "js":
        run(["nim", "js", "-d:release", n])
        print(f"xong {a}.js")
        return

    # 2. Build wasm: Nim -> C -> emcc
    run([
        "nim", "c",
        "--cc:clang",
        "--compileOnly",
        "--cpu:wasm32",
        "--nimcache:.",
        "-d:release",
        n
    ])

    # 3. Tìm file .c do Nim sinh ra
    cfile = f"{a}.nim.c"
    if not os.path.exists(cfile):
        for fn in os.listdir("."):
            if fn.endswith(".c"):
                cfile = fn
                break
    if not os.path.exists(cfile):
        die("Không tìm thấy file .c được Nim tạo ra")

    # 4. Dò include Nim
    nim_include = find_nim_include()
    print(f"[INFO] Using Nim include path: {nim_include}")

    # 5. Biên dịch ra wasm bằng emcc
    run([
        "emcc",
        cfile,
        "-O3",
        "-m32",
        "-s", "STANDALONE_WASM=1",
        "-s", "ERROR_ON_UNDEFINED_SYMBOLS=0",
        "-I", nim_include,
        "-DNIM_INTBITS=32",
        "-o", f"{a}.wasm"
    ])
    print(f"[DONE] Đã tạo {a}.wasm thành công")

if __name__ == "__main__":
    main()
