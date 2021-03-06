from peak.util.symbols import NOT_GIVEN
from peak.util import addons, decorators

__all__ = [
    'parse', 'make_parser', 'get_help', 'Group',
    'Set', 'Add', 'Append', 'Handler', 'reject_inheritance', 'option_handler',
    'attributes', 'AbstractOption', 'InvocationError', 'OptionsRegistry',
]

class InvocationError(Exception):
    """Problem with command arguments or environment"""

class OptionsRegistry(addons.Registry):
    """Registry for option settings"""

    reject_all_inheritance = False

    def created_for(self, cls):
        """Inherit the contents of base classes"""
        old = dict(self)
        addons.Registry.created_for(self, cls)
        if self.reject_all_inheritance:
            for key in list(self):
                if key not in old:
                    self[key] = (None, None)

_optcount = 0

def _gen_key():
    global _optcount
    _optcount +=1
    return _optcount









def reject_inheritance(*names):
    """Reject inheritance of the named options, or all options if none named

    Call this function in a class body to reject inheritance of options
    registered for any of the class' base classes, e.g.::

        class Foo(Bar):
            options.reject_inheritance('-v','--verbose')

    Note that you must list all the variations that you wish to exclude from
    inheritance.  You can also specify no option names, in which case *all*
    inherited options are ignored, and your class will have no options except
    those you explicitly declare.
    """
    r = OptionsRegistry.for_enclosing_class()
    if names:
        for name in names:
            r.set(name, (None, None))
    else:
        r.reject_all_inheritance = True





















def attributes(*classes, **kw):
    """Declare options for attributes

    Use in a class body::

        class MyClass(commands.AbstractCommand):

            db_options = options.Group("Database Options")

            options.attributes(
                dbURL = options.Set(
                    '--db', type=str, metavar="URL", help="Database URL"
                ),
                user = options.Set('--username'),
                ...
            )

    Or outside a class body::

        options.attributes(MyClass,
            dbURL = ...,
            user = ...,
        )
    """
    def register(r):
        for attrname, opts in kw.items():
            try:
                iter(opts)
            except TypeError:
                opts = [opts]
            for option in opts:
                option.register(r, attrname)

    if classes:
        for cls in classes:
            register(OptionsRegistry(cls))
    else:
        register(OptionsRegistry.for_enclosing_class())



class Group:
    """Designate a group of options to be displayed under a common heading

    Example usage::

        class MyClass(commands.AbstractCommand):
            db_options = options.Group("Database Options")

            options.attributes(
                dbURL = options.Set(
                    '--db', type=str, metavar="URL", help="Database URL"
                ),
                user = options.Set('--username'),
                ...
            )

    When help is displayed for the above class, it will list the '--db' option
    under a heading with the title "Database Options", along with any other
    options that have their 'group' set to the 'db_options' object.

    In addition to a title, you may also specify a 'description' (explanatory
    text that will appear under the group's heading and before the options),
    and a 'sortKey'.  If specified, the 'sortKey' will determine the relative
    order of groups' display (groups with lower keys appear first).  Groups
    with the same sort key appear in the same order that they were created in.
    """

    def __init__(self,title,description=None,sortKey=0):
        self.title, self.description, self.sortKey = title,description,sortKey
        self.sort_stable = _gen_key()

    def __repr__(self):
        return "Group"+`(self.title,self.description,self.sortKey)`

    def makeGroup(self,parser):
        from optparse import OptionGroup
        return ((self.sortKey,self.sort_stable),
            OptionGroup(parser,self.title,self.description)
        )


class AbstractOption:
    """Base class for option metadata objects"""
    repeatable = True
    sortKey = 0
    metavar = help = group = None
    value = type = option_names = NOT_GIVEN

    def __init__(self, *option_names, **kw):
        klass = self.__class__
        for k,v in kw.iteritems():
            if hasattr(klass,k):
                setattr(self,k,v)
            else:
                raise TypeError(
                    "%s constructor has no keyword argument %s" % (klass, k)
                )

        if not option_names:
            raise TypeError(
                "%s must have at least one option name"
                % self.__class__.__name__
            )
        self.option_names = option_names
        for option in option_names:
            if not option.startswith('-') or option.startswith('---'):
                raise ValueError(
                    "Invalid option name %r:"
                    " option names must begin with '-' or '--'" % (option,)
                )

        if (self.type is NOT_GIVEN) == (self.value is NOT_GIVEN):
            raise TypeError(
                "%s options must have a value or a type, not both or neither"
                % self.__class__.__name__
            )

        if self.type is NOT_GIVEN and self.metavar is not None:
            raise TypeError(
                "'metavar' is meaningless for options without a type"
            )

        if self.type is not NOT_GIVEN:
            self.nargs = 1
            if self.metavar is None:
                self.metavar = self.type.__name__.upper()
        else:
            self.nargs = 0
        self.sort_stable = _gen_key()


    def makeOption(self, attrname,optmap=None):
        options = self.option_names

        if optmap is not None:
            options = [opt for opt in options if optmap.get(opt) is self]

        from optparse import make_option
        popt = make_option(
            action="callback", nargs=self.nargs, callback_args=(attrname,),
            callback = self.callback, metavar=self.metavar, help=self.help,
            type=(self.type is not NOT_GIVEN and "string" or None),*options
        )
        return (self.sortKey, self.sort_stable), popt

    def convert(self,option,value):
        if self.value is NOT_GIVEN:
            try:
                return self.type(value)
            except ValueError:
                raise InvocationError(
                    "%s: %r is not a valid %s" % (option,value,self.metavar)
                )
        else:
            return self.value


    def register(self, registry, attrname):
        for optname in self.option_names:
            registry.set(optname, (attrname,self))



    def check_repeat(self,option,parser):
        if not self.repeatable:

            if not hasattr(parser,'use_counts'):
                parser.use_counts = {}

            count = parser.use_counts.setdefault(self,0) + 1
            parser.use_counts[self] = count

            if count>1:
                raise InvocationError("%s can only be used once" % option)






























class Set(AbstractOption):
    """Set the attribute to the argument value or a constant"""

    repeatable = False

    def callback(self, option, opt, value, parser, attrname):
        self.check_repeat(option,parser)
        setattr(parser.values, attrname, self.convert(option,value))


class Add(AbstractOption):
    """Add the argument value or a constant to the attribute"""

    def callback(self, option, opt, value, parser, attrname):
        self.check_repeat(option,parser)
        value = getattr(parser.values, attrname) + self.convert(option,value)
        setattr(parser.values, attrname, value)


class Append(AbstractOption):
    """Append the argument value or a constant to the attribute"""

    def callback(self, option, opt, value, parser, attrname):
        self.check_repeat(option,parser)
        getattr(parser.values, attrname, value).append(
            self.convert(option,value)
        )


class Handler(AbstractOption):
    """Invoke a handler method when the option appears on the command line"""

    repeatable = False
    function = None

    def callback(self, option, opt, value, parser, attrname):
        self.check_repeat(option,parser)
        self.function(
            parser.values,parser,opt,self.convert(option,value),parser.rargs
        )

def parse(ob,args,**kw):
    """Parse 'args' into 'ob', returning non-option arguments

    'ob' can be any object whose class has options registered.  'args' must
    be a list of arguments, such as one might find in 'sys.argv[1:]'.  A
    list of all the non-option arguments is returned, and 'ob' will have
    its attributes set or modified according to the defined behavior for
    any options found in 'args'.

    You can also supply any keyword arguments that are accepted by
    'optparse.OptionParser', to configure things like the usage string,
    program name and description, etc.
    """
    opts, args = make_parser(ob,**kw).parse_args(args, ob)
    return args


def get_help(ob,**kw):
    """Return a nicely-formatted help message for 'ob'

    The return value is a formatted help message for any options that are
    registered for the class of 'ob'.

    You can also supply any keyword arguments that are accepted by
    'optparse.OptionParser', to configure things like the usage string,
    program name and description, etc., that are used to format the help.
    """
    return make_parser(ob,**kw).format_help().strip()













def make_parser(ob,**kw):
    """Make an 'optparse.OptionParser' for 'ob'

    The parser will be populated with the options registered for the
    object's class.  Any keyword arguments supplied will be passed
    directly to 'optparse.OptionParser', so see its docs for details.
    By default, this routine sets 'usage' to an empty string,
    'add_help_option' to 'False', and 'allow_interspersed_args' to
    'False', unless you override them.
    """

    kw.setdefault('usage','')
    intersperse = kw.setdefault('allow_interspersed_args',False)
    del kw['allow_interspersed_args']
    prog = kw.setdefault('prog','')+':'
    kw.setdefault('add_help_option',False)

    from optparse import OptionParser
    parser = OptionParser(**kw)
    if not intersperse:
        parser.disable_interspersed_args()

    def _exit_parser(status=0, msg=None):
        if msg:
            if msg.startswith(prog):
                msg = msg[len(prog):]
            raise InvocationError(msg.strip())
        if status:
            raise SystemExit(status)

    parser.exit = _exit_parser
    optinfo = OptionsRegistry(ob.__class__).items()









    optmap = dict([(k,opt)for k,(a,opt) in optinfo if opt is not None])
    optsused = {}
    optlists = {}
    for optname,(attrname,option) in optinfo:
        if option in optsused or option is None:
            continue
        optlists.setdefault(option.group,[]).append(
            option.makeOption(attrname,optmap)
        )
        optsused[option] = True

    groups = []
    for group,optlist in optlists.items():
        if group is None:
            container = parser
        else:
            key,container = group.makeGroup(parser)
            groups.append((key,container))

        optlist.sort()
        for key,popt in optlist:
            container.add_option(popt)

    groups.sort()
    for key,group in groups:
        parser.add_option_group(group)

    return parser













def option_handler(*option_names, **kw):
    """Decorate a method to be called when option is encountered

    Usage::

        class Bar:
            [options.option_handler('-z', type=int, help="Zapify!")]
            def zapify(self, parser, optname, optval, remaining_args):
                print "Zap!", optval

    The 'zapify' function above will be called on a 'Bar' instance if it
    parses a '-z' option.  'parser' is the 'optparse.OptionParser' being used
    to do the parsing, 'optname' is the option name (e.g. '-z') that was
    encountered, 'optval' is either the option's argument or the 'value'
    keyword given to 'option_handler', and 'remaining_args' is the list of
    arguments that are not yet parsed.  The handler function is free to modify
    the list in-place in order to manipulate the handling of subsequent
    options.  It may also manipulate other attributes of 'parser', if desired.
    """

    def decorator(frame,name,func,old_locals):
        Handler(function=func, *option_names,**kw).register(
            OptionsRegistry.for_frame(frame), None
        )
        return func

    return decorators.decorate_assignment(decorator)














