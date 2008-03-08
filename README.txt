============================================================
Command-line Option Processing with ``peak.running.options``
============================================================

.. contents:: **Table of Contents**


-------
Preface
-------

The ``peak.running.options`` module lets you define command-line options for
a class (optionally inheriting options from base classes), and the ability
to parse those options using the Python ``optparse`` library.

``options`` extends optparse by tying option metadata to classes (using
the ``peak.binding`` attribute metadata framework), and allowing classes to
inherit options from their base class(es).  It also uses a much more compact
notation for specifying options than that provided by the "raw" ``optparse``
module, that generally requires less typing to specify an option.

For our examples, we'll need to use the PEAK API and the ``options`` module::

    >>> from peak.api import *
    >>> from peak.running import options


-------------
Framework API
-------------

Parsing Functions
=================

The basic idea of the ``options`` framework is that you have an object whose
attributes will store the options parsed from a command line.  The options that
are available, depend on what options you declared when defining the object's
class, or its base class(es).

All of the ``options`` API functions assume that you have already created the
object you intend to use to store options.  (This works well with the common
case of a ``peak.running.commands`` command object that is calling the parsing
API from within its ``run()`` method.)

These functions also accept keyword arguments that are passed directly to the
``optparse.OptionParser`` constructor.  So, if you need precise control over
some ``optparse`` feature, you can supply keyword arguments to do so.  (Most
often, these arguments will be used to set the `usage`, `description`, and
`prog` values used for creating help messages.  See the section on `Parser
Settings`_ for details.)

``options.make_parser`` (`ob`, `**kw`)
    Make an ``optparse.OptionParser`` for `ob`, populating it with the
    options registered for ``ob.__class__``.

``options.parse`` (`ob`, `args`, `**kw`)
    Parse `args`, setting any options on `ob`, and returning a list of
    the non-option arguments in `args`.  `args` should be a list of
    argument values, such as one might find in ``sys.argv[1:]``.

``options.get_help`` (`ob`, `**kw`)
    Return a formatted help message for `ob`, explaining the options
    registered for ``ob.__class__``.


Declaring Options
=================

Most of the time, you will want command-line options to set or modify some
attribute of your command object.  So, most options are specified as attribute
metadata, e.g. via the ``metadata`` argument of an attribute binding, or
through attribute metadata APIs like ``binding.metadata()`` or
``binding.declareAttributes()``.  For simplicity in this document, we'll be
mostly using ``binding.metadata()``, but you can also specify options like
this::

    class MyClass(commands.AbstractCommand):

        dbURL = binding.Obtain(
            PropertyName('myapp.dburl'),
            [options.Set('--db', type=str, metavar="URL", help="Database URL")]
        )

(That is, by including option declarations as metadata in an attribute binding.)

Anyway, there are three kinds of options that can associate with attributes:

* ``options.Set()``
* ``options.Add()``
* ``options.Append()``

Each kind of option performs the appropriate action on the associated
attribute.  That is, a ``Set()`` option sets the attribute to some value, while
an ``Add()`` or ``Append()`` option adds to or appends to the attribute's
initial value.

Let's take a look at some usage examples::

    >>> opt_x = options.Set('-x', value=True, help="Set 'x' to true")
    >>> opt_v = options.Set('-v', '--verbose', value=True, help="Be verbose")
    >>> opt_q = options.Set('-q', '--quiet', value=False, help="Be quiet")
    >>> opt_f = options.Set('-f', '--file', type=str, metavar="FILENAME")
    >>> opt_p = options.Set('-p', type=int, metavar="PORT", help="Set port")
    >>> opt_L = options.Append('-L', type=str, metavar="LIBPATH", sortKey=99)
    >>> opt_d = options.Add('-d', type=int, help="Add debug flag")

All of these option constructors take the same arguments; one or more option
names, followed by some combination of these keyword arguments:

``type``
    A callable that can convert from a string to the desired option type.
    If supplied, this means that the option takes an argument, and the value
    to be set, added, or appended to the attribute will be computed by calling
    ``supplied_type(argument_string)`` when the option appears in a command
    line.  If the callable raises a ``ValueError``, the error will be converted
    to an ``InvocationError`` saying that the value isn't valid.  All other
    errors propagate to the caller.

``value``
    If supplied, this means that the option does not take an argument, and the
    supplied value will be set, added, or appended to the attribute when the
    option appears in a command line.

``help``
    A short string describing the option's purpose, for use in generating a
    usage message.

``metavar``
    A short string used to describe the argument taken by the attribute.  For
    example, a ``metavar`` of ``"FILENAME"`` might produce a help string like
    ``"-f FILENAME   Set the filename"`` (assuming the option name is ``-f``
    and the ``help`` string is ``"Set the filename"``).  Note that ``metavar``
    is only meaningful when ``type`` is specified.  If no ``metavar``
    is supplied, it defaults to an uppercase version of the ``type`` object's
    ``__name__``, such that ``type=int`` defaults to a metavar of ``"INT"``::

        >>> opt_p.metavar
        'PORT'
        >>> opt_d.metavar
        'INT'

``repeatable``
    A true/false flag indicating whether the option may appear more than once
    on the command line.  Defaults to ``True`` for ``Add`` and ``Append``
    options, and ``False`` for ``Set`` options and ``option_handler`` methods::

        >>> opt_d.repeatable
        1
        >>> opt_L.repeatable
        1
        >>> opt_q.repeatable
        0

``sortKey``
    The sort key is a value used to arrange options in a specified order for
    help messages.  Options with lower ``sortKey`` values appear earlier in
    generated help than options with higher ``sortKey`` values.  The default
    ``sortKey`` is ``0``::

        >>> opt_x.sortKey
        0
        >>> opt_L.sortKey
        99

    Options that have the same ``sortKey`` will be sorted in the order in which
    they were created, so you don't ordinarily need to set this.  (Except to
    insert new options in the display order, ahead of previously-defined
    options.)

``group``
    Set this to an ``options.Group()`` instance, if you want the option to
    appear under that group's heading in any generated help messages.  (See the
    section on `Option Groups`_ for more details.)

Note that an option must have either  a ``type`` (in which case it accepts an
argument), or a ``value`` (in which case it does not accept an argument).  It
must have one or the other, not both.

Note also that more than one option can be specified for a given attribute,
although in that case they will usually all be ``Set(value=someval)`` options.
For example, the ``-v`` and ``-q`` options shown above would most likely be
used with the same attribute, e.g.::

    >>> class Foo:
    ...     binding.metadata(verbose = [opt_v, opt_q])
    ...     verbose = False

For the above class, ``-q`` will set ``verbose`` to ``False``, and ``-v`` will
set it to ``True``.


Option Handlers
---------------

Sometimes, however, it's necessary to do more complex option processing than
just altering an attribute value.  So, you can also create option handler
methods::

    >>> class Foo:
    ...     [options.option_handler('-z', type=int, help="Zapify!")]
    ...     def zapify(self, parser, optname, optval, remaining_args):
    ...         """Do something here"""

``option_handler`` is a function decorator that accepts the same positional
and keyword arguments as an attribute option, but instead of modifying an
attribute, it calls the decorated function when one of the specified options
is encountered on a command line.  You must specify ``repeatable=True`` if you
want to allow the option to appear more than once on the command line.

The ``zapify`` function above will be called on a ``Foo`` instance if it
parses a ``-z`` option.  `parser` is the ``optparse.OptionParser`` being used
to do the parsing, `optname` is the option name (e.g. ``-z``) that was
encountered, `optval` is either the option's argument or the `value`
keyword given to ``option_handler``, and `remaining_args` is the list of
arguments that are not yet parsed.  The handler function is free to modify
the list in-place in order to manipulate the handling of subsequent
options.  It may also manipulate other attributes of `parser`, if desired.


Inheriting Options
------------------

By default, options defined in a base class are inherited by subclasses::

    >>> class Foo:
    ...     binding.metadata(verbose = [opt_v, opt_q])
    ...     verbose = False

    >>> print options.get_help(Foo())
    options:
      -v, --verbose  Be verbose
      -q, --quiet    Be quiet

    >>> class Bar(Foo):
    ...     binding.metadata(libs = opt_L, debug=opt_d)
    ...
    ...     [options.option_handler('-z', type=int, help="Zapify!")]
    ...     def zapify(self, parser, optname, optval, remaining_args):
    ...         print "Zap!", optval

    >>> print options.get_help(Bar())   # doctest: +NORMALIZE_WHITESPACE
    options:
      -v, --verbose  Be verbose
      -q, --quiet    Be quiet
      -d INT         Add debug flag
      -z INT         Zapify!
      -L LIBPATH

    # Even though it was defined after -d, -L is last because its sortKey is 99

But, you can selectively reject inheritance of individual options, by passing
their option name(s) to ``options.reject_inheritance()``::

    >>> class Baz(Foo):
    ...     options.reject_inheritance('--quiet','-v')

    >>> print options.get_help(Baz())
    options:
      --verbose  Be verbose
      -q         Be quiet

Or, you can reject all inherited options and start from scratch, by calling
``options.reject_inheritance()`` with no arguments::

    >>> class Spam(Foo):
    ...     options.reject_inheritance()

    >>> options.get_help(Spam())
    ''



Parsing Examples
================

Let's go ahead and parse some arguments, using ``options.parse()``.  This API
function takes a target object and a list of input arguments, returning a list
of the non-option arguments.  Meanwhile, the target object's attributes
are modified (or its handler methods are called) according to the options found
in the input arguments.

* No options or arguments::

    >>> foo = Foo(); options.parse(foo, [])
    []
    >>> foo.verbose
    0

* An option and an argument::

    >>> foo = Foo(); options.parse(foo, ['-v', 'q'])
    ['q']
    >>> foo.verbose
    1

* Stop processing options after first argument::

    >>> foo = Foo(); options.parse(foo, ['xyz', '-v'])
    ['xyz', '-v']
    >>> foo.verbose
    0

* Unless interspersed arguments are allowed (see `Parser Settings`_ below)::

    >>> foo = Foo()
    >>> options.parse(foo, ['xyz', '-v'], allow_interspersed_args=True)
    ['xyz']
    >>> foo.verbose
    1


* Two options::

    >>> foo = Foo(); options.parse(foo, ['-v', '-q'])
    []
    >>> foo.verbose
    0

* Repeating unrepeatable options::

    >>> foo = Foo(); options.parse(foo, ['-v', '-q', '-v'])
    Traceback (most recent call last):
    ...
    InvocationError: -v/--verbose can only be used once

    >>> bar = Bar(); options.parse(bar, ['-z','20', '-z', '99'])
    Traceback (most recent call last):
    ...
    InvocationError: -z can only be used once

* Using an invalid value for the given type converter::

    >>> bar = Bar(); options.parse(bar, ['-z','foobly'])
    Traceback (most recent call last):
    ...
    InvocationError: -z: 'foobly' is not a valid INT

* Option handler called in the middle of parsing::

    >>> bar = Bar(); options.parse(bar, ['-z','20', '-v', 'xyz'])
    Zap! 20
    ['xyz']
    >>> bar.verbose
    1

* ``Append`` option with multiple values, specified in different ways::

    >>> bar = Bar(); bar.libs = []
    >>> options.parse(bar, ['-Labc','-L', 'xyz', '123'])
    ['123']
    >>> bar.libs
    ['abc', 'xyz']

* ``Add`` option with multiple values, specified in different ways::

    >>> bar = Bar(); bar.debug = 0
    >>> options.parse(bar, ['-d23','-d', '32', '321'])
    ['321']
    >>> bar.debug
    55

* Unrecognized option::

    >>> foo = Foo()
    >>> options.parse(foo, ['--help'])
    Traceback (most recent call last):
    ...
    InvocationError: ... no such option: --help


Help/Usage Messages
===================

By default, PEAK doesn't include a ``--help`` option in the options for an
arbitrary class, so if you want one, you have to create your own.  (Unless
you're using a ``commands`` framework base class, in which case it may be
provided for you.)  Here's one way to implement such an option::

    >>> class Test(Bar):
    ...     options.reject_inheritance('-L', '-d')
    ...     [options.option_handler('--help',value=None,help="Show help")]
    ...     def show_help(self, parser, optname, optval, remaining_args):
    ...         print parser.format_help().strip()
    >>> test = Test()
    >>> args = options.parse(test, ['--help'])
    options:
      -v, --verbose  Be verbose
      -q, --quiet    Be quiet
      -z INT         Zapify!
      --help         Show help

(Of course, for command objects, the help should actually be sent to the
command's standard out or standard error, rather than to ``sys.stdout`` as is
done in this example.)


Parser Settings
---------------

As we mentioned earlier, you can pass ``optparse.OptionParser`` keywords to
any of the `Parsing Functions`_.  Most often, you'll want to set the `usage`,
`prog`, and `description` keywords, in order to control the content of
generated help messages.  For example::

    >>> args = options.parse(test, ['--help'],
    ...     usage="%prog [options]", description="Just a test program.",
    ...     prog="Test",
    ... )
    usage: Test [options]
    ...
    Just a test program.
    ...
    options:
      -v, --verbose  Be verbose
      -q, --quiet    Be quiet
      -z INT         Zapify!
      --help         Show help

(By the way, the ``...`` lines in the sample output shown above are actually
blank lines in the real output.  Doctest doesn't allow blank lines to appear
in sample output.)

Also, one keyword argument is allowed that is not actually an ``OptionParser``
keyword argument: ``allow_interspersed_args``.  If this keyword is not set
to a true value, option parsing stops at the first non-option argument
encountered.  (This is the desired default behavior for PEAK commands, to
prevent them trying to parse subcommands' options.)


Option Groups
-------------

Finally, if you have a class with many options, you may want the help to
display the options in groups, using ``options.Group``.  Groups have the
following properties that can be set:

``title``
    This sets the title that will be displayed for the option group in help
    messages.

``description``
    This sets additional text, if any, that should appear after the group
    title, but before the options in that group are listed.  ``optparase``
    treats this as a single paragraph of text and may rewrap it, so don't
    bother with any fancy formatting.

``sortKey``
    The sort key is a value used to arrange groups in a specified order.
    Groups with lower ``sortKey`` values appear earlier in generated help than
    groups with higher ``sortKey`` values.  The default ``sortKey`` is ``0``.

    Groups that have the same ``sortKey`` will be sorted in the order in which
    they were created, so you don't ordinarily need to set this, except to
    insert new groups in the display order, ahead of previously-defined
    groups.

These arguments may be specified positionally, or with keywords::

    >>> silly = options.Group(
    ...     "Silly Options",
    ...     "Forward aerial half turn every alternate step",
    ... )
    >>> silly.title
    'Silly Options'
    >>> silly.description
    'Forward aerial half turn every alternate step'
    >>> silly.sortKey
    0

    >>> trendy = options.Group(title="Trendy Options", sortKey=10)
    >>> trendy.title
    'Trendy Options'
    >>> trendy.sortKey
    10
    >>> trendy.description is None
    1

Option groups are then specified as part of the definition of an option, to
place that option in the corresponding group::

    >>> dangerous = options.Group("DANGER")
    >>> opt_explode = options.Set('--explode', value="BOOM", help="Explode!",
    ...     group=dangerous)

    >>> opt_r = options.Set('-r', '--request-grant', type=float,
    ...     help="Request grant from the Ministry", group = silly
    ... )
    >>> opt_r.group
    Group('Silly Options', 'Forward aerial half turn every alternate step', 0)

Once this is done, the option can be placed in a class with other options::

    >>> class Groupy(Foo):
    ...     binding.metadata(money=opt_r, bang=opt_explode)
    >>> print options.get_help(Groupy())
    options:
      -v, --verbose         Be verbose
      -q, --quiet           Be quiet
    ...
      Silly Options:
        Forward aerial half turn every alternate step
    ...
        -r FLOAT, --request-grant=FLOAT
                            Request grant from the Ministry
    ...
      DANGER:
        --explode           Explode!

As you can see, even though ``--explode`` is defined *before*
``--request-grant``, it is in a group that is defined *after* the group that
``--request-grant`` is in, so it appears later, because the options are
separated according to group.  Meanwhile, options that don't appear in any
group are simply placed under the first heading.  If you don't have any
ungrouped options, then the output looks more like this::

    >>> class GroupsOnly:
    ...     binding.metadata(money=opt_r, bang=opt_explode)
    >>> print options.get_help(GroupsOnly())
    options:
      Silly Options:
        Forward aerial half turn every alternate step
    ...
        -r FLOAT, --request-grant=FLOAT
                            Request grant from the Ministry
    ...
      DANGER:
        --explode           Explode!


Using Options with Commands
===========================

Now let's take a look at how to integrate options with command objects from
``peak.running.commands``.  First, we'll define a command class with a few
options::

    >>> class MyCommand(commands.AbstractCommand):
    ...     bang = binding.Make(
    ...         lambda: NOT_GIVEN,
    ...         [opt_explode, opt_v, opt_q]    # bind options to this attribute
    ...     )

And let's see what its help output now looks like::

    >>> import sys
    >>> from peak.tests import testRoot
    >>> exitcode = MyCommand(testRoot(),stderr=sys.stdout).showHelp()
    Either this is an abstract command class, or somebody forgot to
    define a usage message for their subclass.
    ...
    options:
      -v, --verbose  Be verbose
      -q, --quiet    Be quiet
      --help         Show help
    ...
      DANGER:
        --explode    Explode!
    ...

As you can see, the option information is now part of the help output produced
by the command.  Also, we see that the ``--help`` option is automatically
defined for us by ``commands.AbstractCommand``.  It will invoke the command's
``showHelp()`` method, so we can override how it actually works in our subclass
if we need to.

To actually parse the options supplied to a command, we need only reference its
``parsed_args`` attribute.  This will cause argument parsing to occur if it
hasn't already, updating any attributes associated with the options, and
returning the non-option arguments from the command line::

    >>> cmd = MyCommand(testRoot(),argv=['foo','--explode','spam'])
    >>> cmd.bang
    NOT_GIVEN
    >>> cmd.parsed_args
    ['spam']
    >>> cmd.bang
    'BOOM'

As you can see, the ``bang`` attribute had its default value until we looked
at ``parsed_args``, at which point it was set according to the supplied
options.  (Note: the ``"foo"`` in the ``argv`` parameter is the "program name",
which is why it doesn't appear in ``cmd.parsed_args``.)

Finally, you should be aware that both the help generation and option parsing
are done via the ``option_parser`` attribute of the command, which is
automatically populated using ``options.make_parser(self)``.  You can therefore
access it directly, or override the binding in a subclass to change how the
parser gets set up.

::

    >>> cmd.option_parser
    <...OptionParser...>

So there you have it.  Metadata-driven option parsing, seamlessly integrated
with the ``peak.running.commands`` framework.  The rest of this document
deals strictly with implementation details, so you don't need or want to read
it unless you're trying to track down a bug in the framework itself, or want
to learn more about how it works internally.



------------------------
Framework Implementation
------------------------


``options.AbstractOption``
==========================

The ``AbstractOption`` class is a base class used to create command-line
options.  Instances are created by specifying a series of option names, and
optional keyword arguments to control everything else.  Here are some examples
of correct ``AbstractOption`` usage::

    >>> opt=options.AbstractOption('-x', value=42, sortKey=100)
    >>> opt=options.AbstractOption('-y','--yodel',type=int,repeatable=False)
    >>> opt=options.AbstractOption('--trashomatic',type=str,metavar="FILENAME")
    >>> opt=options.AbstractOption('--foo', value=None, help="Foo the bar")

A valid option spec must have one or more option names, each of which begins
with either '-' or '--'.  It may have a ``type`` OR a ``value``, but not both.
It can also have a ``help`` message, and if the ``type`` is specified you
may specify a ``metavar`` used in creating usage output.  You may also specify
whether the option is repeatable or not.  If your input fails any of these
conditions, an error will occur::

    >>> options.AbstractOption(foo=42)
    Traceback (most recent call last):
    ...
    TypeError: ... constructor has no keyword argument foo
    >>> options.AbstractOption()
    Traceback (most recent call last):
    ...
    TypeError: ... must have at least one option name
    >>> options.AbstractOption('x')
    Traceback (most recent call last):
    ...
    ValueError: ... option names must begin with '-' or '--'
    >>> options.AbstractOption('---x')
    Traceback (most recent call last):
    ...
    ValueError: ... option names must begin with '-' or '--'

    >>> options.AbstractOption('-x', value=42, type=int)
    Traceback (most recent call last):
    ...
    TypeError: ... options must have a value or a type, not both or neither
    >>> options.AbstractOption('-x', value=42, metavar="VALUE")
    Traceback (most recent call last):
    ...
    TypeError: 'metavar' is meaningless for options without a type


The ``makeOption()`` Method
---------------------------

``AbstractOption`` instances should also be able to create ``optparse`` option
objects for themselves, via their ``makeOption(attrname)`` method.  The
method should return a ``(key,parser_opt)`` tuple, where ``key`` is a sort key,
and ``parser_opt`` is an ``optparse.Option`` instance configured with a callback
set to the option's ``callback`` method, an appropriate number of arguments
(``nargs``), and callback arguments containing the attribute name (so the
callback will know what attribute it's supposed to affect).  In addition, the
created option's ``help`` and ``metavar`` should be the same as those on the
original option::

    >>> key, xopt = opt_x.makeOption('foo')
    >>> xopt.action
    'callback'
    >>> xopt.nargs
    0
    >>> xopt.callback == opt_x.callback
    1
    >>> xopt.callback_args
    ('foo',)
    >>> xopt.metavar is None
    1
    >>> xopt.help is opt_x.help
    1

    >>> key, popt = opt_p.makeOption('bar')
    >>> popt.nargs
    1
    >>> popt.callback == opt_p.callback
    1
    >>> popt.callback_args
    ('bar',)
    >>> popt.metavar
    'PORT'

In addition, the ``makeOption()`` method accepts an optional ``optmap``
parameter, that maps from option names to option objects.  If this map is
supplied, the created option will only include option names that are present
as keys in ``optmap``, and whose value in ``optmap`` is the original option
object.  For example::

    >>> print opt_f.makeOption('baz')[1]
    -f/--file
    >>> print opt_f.makeOption('baz', {'-f':opt_f})[1]
    -f
    >>> print opt_f.makeOption('baz', {'--file':opt_f})[1]
    --file
    >>> print opt_f.makeOption('baz', {'--file':opt_f, '-f':opt_f})[1]
    -f/--file

Note, however, that this isn't a search through the ``optmap``, it's just a
check for the option names the option already has::

    >>> print opt_f.makeOption('baz', {'--foo':opt_f})[1]
    Traceback (most recent call last):
    ...
    TypeError: at least one option string must be supplied



``options.OptionRegistry``
==========================

The ``options.OptionRegistry`` is a dispatcher that manages option metadata
for any class that has command-line options.  When an option is declared
as metadata for an attribute, it is added to the registry.  Here, we check
that the 'method' passed to the registry's ``__setitem__`` is correct::

    >>> from peak.util.unittrace import History
    >>> class Foo: pass
    >>> option_x = options.AbstractOption('-x',value=True)
    >>> h = History()
    >>> h.trace(binding.declareAttribute, Foo, 'bar', option_x)
    >>> h.calledOnce(options.OptionRegistry.__setitem__).args.method
    (('-x', ('bar', <...AbstractOption...>)),)

The registered value for an option is a tuple of ``(optname,(attr,option))``
tuple structures, one for each option name in the option object.  This is then
turned into more useful information by the option registry's method combiner::

    >>> options.OptionRegistry[Foo(),]
    {'-x': ('bar', <...AbstractOption...>)}

Although, it's probably easier to see the usefulness with a more elaborate
example::

    >>> class Foo:
    ...     binding.metadata(
    ...         bar = options.AbstractOption('-x','--exact',value=True),
    ...         baz = options.AbstractOption('-y','--yodeling',value=False),
    ...     )
    >>> options.OptionRegistry[Foo(),]  # doctest: +NORMALIZE_WHITESPACE
    {'--exact': ('bar', <...AbstractOption...>),
    '-y': ('baz', <...AbstractOption instance...>),
    '-x': ('bar', <...AbstractOption instance...>),
    '--yodeling': ('baz', <...AbstractOption instance...>)}


-----
To Do
-----

* Help formatter column setting, style setting
* Allow multi-valued args (``nargs>1``)?

