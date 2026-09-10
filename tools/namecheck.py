import ast, builtins, json, re, sys, glob
BUILT = set(dir(builtins))
def strip_magics(src):
    out, skip = [], False
    for l in src.split('\n'):
        if skip: out.append(''); skip = l.rstrip().endswith('\\'); continue
        m = re.match(r'^(\s*)[!%]', l)
        if m: out.append(m.group(1)+'pass'); skip = l.rstrip().endswith('\\')
        else: out.append(l)
    return '\n'.join(out)

class Scope(ast.NodeVisitor):
    """collect names bound at module level, and names loaded anywhere"""
    def __init__(self): self.bound, self.used = set(), []
    def visit_FunctionDef(self, n):
        self.bound.add(n.name)
        inner = set(a.arg for a in n.args.args + n.args.kwonlyargs)
        if n.args.vararg: inner.add(n.args.vararg.arg)
        if n.args.kwarg: inner.add(n.args.kwarg.arg)
        sub = Scope(); [sub.visit(c) for c in n.body]
        self.used += [(u, ln) for u, ln in sub.used if u not in inner and u not in sub.bound]
    visit_AsyncFunctionDef = visit_FunctionDef
    def visit_Lambda(self, n):
        inner = set(a.arg for a in n.args.args)
        sub = Scope(); sub.visit(n.body)
        self.used += [(u, ln) for u, ln in sub.used if u not in inner]
    def visit_comprehension_generic(self, n):
        inner = set()
        for g in n.generators:
            for t in ast.walk(g.target):
                if isinstance(t, ast.Name): inner.add(t.id)
        sub = Scope(); [sub.visit(c) for c in ast.iter_child_nodes(n)]
        self.used += [(u, ln) for u, ln in sub.used if u not in inner]
    visit_ListComp = visit_SetComp = visit_GeneratorExp = visit_comprehension_generic
    def visit_DictComp(self, n): self.visit_comprehension_generic(n)
    def visit_Name(self, n):
        (self.bound.add(n.id) if isinstance(n.ctx, (ast.Store, ast.Del)) else self.used.append((n.id, n.lineno)))
    def visit_alias(self, n): self.bound.add((n.asname or n.name).split('.')[0])
    def visit_Import(self, n): [self.visit_alias(a) for a in n.names]
    def visit_ImportFrom(self, n): [self.visit_alias(a) for a in n.names]
    def visit_ClassDef(self, n): self.bound.add(n.name); self.generic_visit(n)
    def visit_ExceptHandler(self, n):
        if n.name: self.bound.add(n.name)
        self.generic_visit(n)
    def visit_Global(self, n): self.bound.update(n.names)

for nb_path in sorted(glob.glob(sys.argv[1])):
    nb = json.load(open(nb_path)); known = set(); bad = []
    for i, c in enumerate(nb['cells']):
        if c['cell_type'] != 'code': continue
        src = strip_magics(''.join(c['source']))
        sc = Scope(); [sc.visit(n) for n in ast.parse(src).body]
        for u, ln in sc.used:
            if u not in known and u not in sc.bound and u not in BUILT: bad.append((i, ln, u))
        known |= sc.bound
    print(f"{nb_path.split('/')[-1]:26s} " + ('OK' if not bad else 'UNDEFINED: ' + ', '.join(f'cell {i} line {l}: {u}' for i, l, u in bad)))
