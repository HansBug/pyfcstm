.. _sec-explanations-visualization:

Diagram viewer explanation
==========================

``StateMachine.diagram()`` answers a different question from ``pyfcstm plantuml``.
PlantUML gives text you can put under version control; the diagram viewer gives one
file you can open on a machine with no network, no PlantUML, and no pyfcstm — and
which shows the model's own source beside the picture, when the model kept one.

This page explains why that shape, and the consequences a caller has to plan around:
what a snapshot is detached from, why the document is one large file, why ``--open``
blocks, why the privacy boundary is a directory rather than a file, and when the
temporary directory is reclaimed. It is not the option catalogue — use
:doc:`/reference/visualization_options/index` for exact fields and
:doc:`/reference/cli/index` for exact command forms — and not a task recipe; use
:doc:`/how_to/visualization/index` for those.

Two artefacts from one snapshot
-------------------------------

:meth:`pyfcstm.model.model.StateMachine.diagram` returns a
:class:`pyfcstm.diagram.api.Diagram`, and everything else derives from it:

.. list-table:: What the snapshot produces
   :header-rows: 1
   :widths: 22 30 48

   * - Surface
     - Output
     - What it is for
   * - ``to_dict`` / ``to_json``
     - Portable description
     - Feeding another renderer, a diff, or a test. Carries no local paths and no
       editor selection state, so two machines produce the same bytes.
   * - ``to_html`` / ``save`` / ``show``
     - One self-contained document
     - Reading offline. Carries the renderer, layout engine, rasteriser, fonts and
       the model's source, so it needs nothing installed.
   * - ``with_options`` / ``with_view_state``
     - Another snapshot
     - Asking a different question of the same captured model.

Why the snapshot is detached from the model
-------------------------------------------

The snapshot is taken once, at ``diagram()``, and copied out of the model. Editing
the model afterwards cannot change what an already-saved view shows, and attribute
assignment on a :class:`pyfcstm.diagram.api.Diagram` is refused rather than silently
accepted.

The alternative — a live view holding a reference to the model — fails in a way that
is hard to notice. Consider a script that captures a view, mutates the model to
explore a variant, then writes both:

.. code-block:: text

   view = machine.diagram()          # intended: the model as it is now
   machine.add_state(...)            # exploring a variant
   view.save("before.html")          # a live view would render the variant here

With a live view, ``before.html`` would show the *variant*, and nothing in the run
would say so. The immutability is not a purity preference; it is what makes the name
``before.html`` true.

``with_options`` and ``with_view_state`` return new snapshots for the same reason: a
caller who keeps a reference to compare two option sets has two objects, not one
object with a history.

Why one self-contained document
-------------------------------

The viewer is roughly 29 MB -- 29,397,900 bytes for ``state Root;`` loaded from text,
measured here; the exact number moves with the model and with the packaged assets -- and
that is a deliberate trade:

.. list-table:: What the size buys, and what it costs
   :header-rows: 1
   :widths: 34 66

   * - Property
     - Consequence
   * - No network request, ever
     - The document opens on an air-gapped machine, from a mail attachment, or from
       an archive years later. Nothing can rot out from under it.
   * - Renderer, layout engine, rasteriser and CJK fonts embedded
     - The picture is identical wherever it is opened, including the fonts, which is
       what makes a CJK model readable off the original machine.
   * - The model's source travels with it, when the model kept one
     - The source-to-diagram comparison works offline. It also means the document is
       as sensitive as the model. A model that never had source text is the boundary
       below.
   * - One file per document, not per call
     - A kept viewer is named from the document, so asking twice for the same
       diagram returns the same file. Three runs of one script leave one 29 MB file
       rather than three.

That last row is the reason the name is derived from the document rather than being
random. It is also where a caller has to be careful, which
`What sharing a name costs`_ covers.

Where the source half does not apply
------------------------------------

The comparison needs a model that kept both its source *and* the ranges that say where
each state was declared, which in practice means one loaded through
:func:`pyfcstm.model.load.load_state_machine_from_text` or its file counterpart. A
:class:`pyfcstm.model.model.StateMachine` assembled in Python has neither, so the viewer
renders the diagram and says why the other half is missing rather than showing an empty
pane:

.. code-block:: text

   sourceAvailable: False
   sourceUnavailableReason: This model retained neither its original FCSTM source nor
     the ranges that link a state to it; load it through
     load_state_machine_from_file/text. Source text on its own is not enough, because
     the ranges come from parsing.

Passing ``source_text`` without ranges does not get you half of it. The ranges come
from parsing, so text alone leaves nothing to link a state to, and the viewer treats that
as unavailable rather than showing a pane where clicking a state does nothing:

.. code-block:: text

   sourceAvailable: False
   sourceUnavailableReason: This model carries source text but no source ranges, so the
     diagram cannot be linked to it. Ranges come from parsing; a model built
     programmatically has none.

Why the viewer refuses the network
----------------------------------

Because the document carries the model's source, a viewer that could talk to the
network would be a way for a diagram to send a model somewhere. The policy is
therefore not "no external assets" but "no requests at all": ``default-src 'none'``,
``connect-src 'none'``, script hashes rather than a nonce-only allowance,
``base-uri`` and ``form-action`` set to ``'none'``, and no ``eval`` or
``new Function``. ``wasm-unsafe-eval`` is the single exception, and it is what the
embedded rasteriser needs to run at all.

The claim is checked rather than asserted: ``make diagram_csp_check`` verifies
sixteen properties of the emitted document, including that the fonts are embedded,
that the page reaches the network zero times, and that neither ``eval`` nor
``new Function`` appears.

Why ``--open`` blocks
---------------------

``show()`` with a window behaves like ``matplotlib.pyplot.show()``: it returns when
the window closes. That is not a limitation to work around — it is what makes the
temporary file's lifetime ownable.

.. list-table:: Who removes the document
   :header-rows: 1
   :widths: 30 34 36

   * - Call
     - Path
     - Removal
   * - ``show()``
     - A fresh temporary path, one per call
     - This call, when the window closes
   * - ``show(output=...)``
     - The path you named
     - Nobody; it is yours
   * - ``show(open_window=False)``
     - A path derived from the document
     - Nobody; see the next section

A non-blocking ``--open`` would leave nobody able to answer the third column for the
first row. The document would have to survive the process, because the browser reads
it after the call returns — and at roughly 29 MB each, "survive the process" means
"accumulate".

The window also gets a private browser profile, for a reason worth stating: a
Chromium-family browser hands the document to an already-running instance and exits at
once rather than staying to own the window. Blocking on that process would therefore
return immediately, and the document would be removed while the window was still
open. A profile of its own is what makes the process the caller waits on the
process that owns the window.

Why the privacy boundary is a directory
---------------------------------------

A viewer written 0600 is not private enough, and the reason is that ``stat`` needs no
permission on the file it is asked about:

.. list-table:: What another local user can learn, and from where
   :header-rows: 1
   :widths: 40 30 30

   * - Fact
     - Needs
     - Hidden by 0600?
   * - The document's contents
     - Read on the file
     - Yes
   * - The document's name
     - Read on the *directory*
     - No
   * - The document's exact size
     - ``stat`` on the file
     - No
   * - That the directory exists
     - ``x`` on the parent
     - Not even by 0700

The two middle rows are not the same kind of leak, and it is worth being precise
because the design rests on it.

A name derived from the document is a *strong* fingerprint: render candidate models
offline, hash each one, and the name matches exactly or not at all.

The size is a *coarse* side channel, and it collides readily. Four one-state models
whose source text is the same length produce documents of identical length -- and, as
the digests below show, of different content, which is why their names differ while
their sizes do not:

.. code-block:: text

   29397900  sha 5ab7ea2b6fb891d8  state Root;
   29397900  sha 5c0d65bb553a9654  state Boot;
   29397900  sha 32873dcdfc7523e9  state Test;
   29397900  sha 73773c2d5eb47a00  state AAAA;

The embedded assets dominate the length, so a size match narrows the field rather than
naming a model. It is still information a caller did not choose to publish.

Renaming the file would close the first leak and leave the second. Neither is closed by
*any* mode on the file, because ``stat`` does not need one — so the boundary has to be
the directory, which closes both. Viewers go in a per-user directory whose mode is
0700, verified before each use rather than remembered as verified: a directory, not a
symlink, owned by this user, closed to everyone else. When the predictable name cannot
be trusted, the process makes a private one of its own and says so in a warning.

What is left visible is that such a directory exists, when it last changed, and — on a
filesystem whose directory size grows with its entries — roughly how many things are
in it. None of that identifies a model, which is what the fingerprint did.

What sharing a name costs
-------------------------

Reuse follows the *directory*, not the process. Two consequences a caller has to plan
around:

.. code-block:: text

   # Two unrelated processes, same trusted directory, same model:
   process 1: .../pyfcstm-viewers-1000/kept-5ab7ea2b6fb891d8.html
   process 2: .../pyfcstm-viewers-1000/kept-5ab7ea2b6fb891d8.html
   process 2 removes what it was handed
   process 1's path: no such file

A forked child inherits the resolved directory, so it is handed the same path its
parent was. That is the same rule, not a special case — and it is why "each process
keeps its own" would be the wrong way to describe the fallback: the unit is the
directory.

So a kept viewer is shared for removal too. Pass an explicit output path when you
need a document only you may remove.

When the temporary directory is reclaimed
-----------------------------------------

This section is about the directory a process makes for itself, which happens only
when the predictable per-user name cannot be trusted. The trusted directory is *not*
reclaimed and is not meant to be: it is the one whose name carries reuse, so a viewer
left in it is found again by the next process, and an empty one costs nothing and is
used again. What follows applies to the other kind.

A caller who keeps a viewer in such a directory and later removes it leaves it empty,
and nothing in the call that made it is still running to notice. So the reclaim happens
at exit — and *where* at exit is the whole difference between working and not:

.. image:: exit_phases.puml.svg
   :alt: The three phases of multiprocessing's exit function, with the reclaim in the
         last one, after the children are joined.

The claim the diagram makes is that priority is not a detail. ``_exit_function`` runs
finalizers at priority zero and above, *then* terminates daemon children and joins
every child still active, *then* runs what is left. A worker still holding the viewer it was handed has not removed it during
the first of those, so a reclaim there finds the directory occupied and spends its one
chance. Negative priority puts it in the third phase, after the join. Measured on
CPython 3.7 through 3.14, on ``fork``, ``spawn`` and ``forkserver``: at priority zero
the worker has not finished; in the last phase it has.

Two registrations can therefore run in one exit, and which goes first is the order the
caller happened to show and start in:

.. list-table:: The two orders a caller produces
   :header-rows: 1
   :widths: 30 70

   * - Order
     - What happens
   * - start, then show
     - ``multiprocessing.util`` is already imported, so both the ``atexit`` hook and
       the finalizer exist. ``atexit`` runs the later registration first, so the hook
       meets a directory the worker still holds; the finalizer, after the join, finds
       it empty.
   * - show, then start
     - Importing ``multiprocessing`` does not import its ``util``, so no finalizer is
       registered at all. ``util``'s own hook is then the later registration, runs
       first, and joins the worker before this package's hook looks at the directory.

Whichever succeeds leaves the other looking at a directory that has gone, which is why
``ENOENT`` is graded as the outcome asked for rather than as a failure.

What no exit hook reaches is a process that leaves without running any: ``os._exit`` by
hand, or a signal. Such a process leaves one empty directory behind, and only where the
predictable name could not be trusted in the first place. Nothing here can reclaim it,
because the bookkeeping is per process — another process's leftovers are invisible, and
sweeping the temporary directory by name would race a process sitting between creating
its own and writing into it.

Where the platform limits the promise
-------------------------------------

The directory check means what it says on POSIX, where both the mode and the owner can
be asked about. On Windows it still asks whether the path exists and whether ``os.lstat``
reports a directory rather than a link or a file -- what it cannot ask is who owns it and
who else may look: an owner exists there and is readable through the platform's security
API, but the portable ``os.lstat`` and ``os.geteuid`` this package uses do not report it.

``os.mkdir`` does apply a restrictive ACL for a mode of 0o700 on Windows, from the
releases that carried CVE-2024-4030 -- 3.8.20, 3.9.20, 3.10.15, 3.11.10 and 3.12.4 --
and on 3.13 and every line after it, 3.14 included, where it is the line's own released
behaviour rather than a backport. Any other mode is ignored there, and so is 0o700
before those releases. Each of those four backports arrived after python.org had stopped
shipping Windows installers for its line, so the practical rule is shorter than the
list: with an installer from python.org the ACL is there from 3.12.4 onwards and not
below it. A self-built or redistributed interpreter of 3.8.20, 3.9.20, 3.10.15 or
3.11.10 has it. Privacy there rests on ``%TEMP%`` being per
account, which is the default; a ``TEMP`` pointing at a directory other users share is
not detectable from inside the process, and in that case neither the directory nor the
0600 on the files inside it keeps anything private, because that mode is only Windows'
read-only bit.

The advice that follows is the same one the sharing section reaches: pass an explicit
output path for a document that must not be somewhere shared, or that only you may
remove.

How regions are drawn
---------------------

A state that owns regions runs them one after another in declaration order, as
:doc:`How a cycle runs a model with regions </explanations/region_semantics/index>`
explains. A region is therefore not a state: it is never the target of a
transition, it has no entry or exit of its own, and it is not "active" the way a
state is. It is a named, ordered part of its owner. Every output draws it that
way, as a divided area of the owner, and not as a box of its own:

.. list-table:: How each output carries a region
   :header-rows: 1
   :widths: 26 74

   * - Output
     - Region form
   * - PlantUML (``pyfcstm plantuml``)
     - A concurrent-state partition: the regions of one owner are separated by
       ``--`` and each begins with a note that reads ``region N: Name``.
   * - Diagram snapshot (``to_dict`` / ``to_json``, ``pyfcstm diagram``)
     - A child node of the owner with ``region: true`` and an ``ordinal``.
   * - HTML viewer and VS Code preview
     - The regions side by side inside the owner's frame, separated by dashed
       dividers, with no border of their own and the same ``region N: Name``
       title.

.. code-block:: console

   $ pyfcstm plantuml -i controller.fcstm
   ...
       state "Running" as controller__running <<composite>> {
           note as controller__running__safety
               **region 1: Safety**
           end note
           state "Watching" as controller__running__safety__watching
           [*] --> controller__running__safety__watching
           --
           note as controller__running__motion
               **region 2: Motion**
           end note
           state "Off" as controller__running__motion__off
           state "On" as controller__running__motion__on
           [*] --> controller__running__motion__off
           controller__running__motion__off --> controller__running__motion__on : permit != 0 && requested != 0
           controller__running__motion__on --> controller__running__motion__off : permit == 0 || requested == 0
       }
   ...
   $ pyfcstm plantuml -i controller_swapped.fcstm
   ...
               **region 1: Motion**
   ...
           --
           note as controller__running__safety
               **region 2: Safety**
   ...
   $ pyfcstm plantuml -i controller.fcstm -c max_depth=2
   ...
       state "Running" as controller__running <<composite>> {
           note as controller__running__safety
               **region 1: Safety**
           end note
           state "..." as controller__running__safety___collapsed_
           --
           note as controller__running__motion
               **region 2: Motion**
           end note
           state "..." as controller__running__motion___collapsed_
       }
   ...

Read the three parts of the output in turn:

1. In the first block ``--`` separates ``Safety`` from ``Motion``. Each region
   keeps its own ``[*]`` initial arrow and its own transitions, and there is no
   arrow between the two regions, because none can exist.
2. In the second block the same two regions are written in the other order. Only
   the numbers and the order of the partitions change: ``N`` is the position in
   the source, which is also the order in which the regions run. A reader of the
   picture can therefore read the execution order straight off it.
3. In the third block ``max_depth=2`` collapses what is inside the regions but
   keeps the regions. A region counts as one layer of depth, like a state would.

The snapshot carries the same facts as data:

.. testcode::

   from pyfcstm.model import load_state_machine_from_text


   def outline(node, depth=0):
       mark = "  region ordinal=%d" % node["ordinal"] if node.get("region") else ""
       print("  " * depth + node["id"] + mark)
       for child in node["children"]:
           outline(child, depth + 1)


   for name in ("controller", "controller_swapped"):
       machine = load_state_machine_from_text(open(name + ".fcstm").read())
       print("==", name)
       outline(machine.diagram().to_dict()["rootState"])

.. testoutput::

   == controller
   Controller
     Controller.Idle
     Controller.Running
       Controller.Running.Safety  region ordinal=1
         Controller.Running.Safety.Watching
       Controller.Running.Motion  region ordinal=2
         Controller.Running.Motion.Off
         Controller.Running.Motion.On
   == controller_swapped
   Controller
     Controller.Idle
     Controller.Running
       Controller.Running.Motion  region ordinal=1
         Controller.Running.Motion.Off
         Controller.Running.Motion.On
       Controller.Running.Safety  region ordinal=2
         Controller.Running.Safety.Watching

The children of ``Controller.Running`` come out in writing order, and
``ordinal`` is one-based. The layout step below depends on exactly this field.

The viewer draws the same structure. This sketch is hand-drawn to show the
form; it is not output of the viewer:

.. code-block:: text

   Schematic, a top-to-bottom diagram:

   +-- Running ----------------------------------------------+
   |  region 1: Safety       :  region 2: Motion               |
   |                         :                                 |
   |  [*] -> (Watching)      :  [*] -> (Off) <-> (On)          |
   +----------------------------------------------------------+
                             ^ dashed divider

Why divided areas and not states: a state-shaped box would invite the reading that
an arrow can end on it, or that the owner "is in" the region the way it is in a
state. A divider says the opposite: the areas are parts of one thing, there is
no way from one to the other, and the left-to-right or top-to-bottom order is the
only relation between them. An earlier form drew a dashed frame around every
region; the divider form replaced it so that the regions read as parts of one
owner.

What is deliberately **not** drawn is everything that exists only because of
lowering. A guard written with ``active("...")`` keeps its full path, and the
hidden flag variables and the automatic writes to them do not appear.

These commands are not run by the documentation check, because the model file belongs to the diagnostics page and not to this one. The text below is a selection of their recorded output: the legend and the guard lines of the PlantUML text, then the names of the variables and the guard labels of the snapshot.

.. code-block:: bash

   pyfcstm plantuml -i region_written_vs_running.fcstm
   pyfcstm diagram -i region_written_vs_running.fcstm

.. code-block:: text

   | go | int | N/A | input |
   | lamp | int | 0 | output |
       panel__lamp__dark --> panel__lamp__lit : active("Panel.Switch.Pressed")
       panel__lamp__dark --> panel__lamp__lit : active("Panel.Switch.Pressed") && !active("Panel.Switch.Pressed")

   variables: go, lamp
   guards: active("Panel.Switch.Pressed"), active("Panel.Switch.Pressed") && !active("Panel.Switch.Pressed"), go != 0, go == 0

The model is the one from :doc:`Diagnostics explanation </explanations/diagnostics/index>`.
Neither the legend nor the snapshot's variable list shows an ``__active_*``
variable, while a finding of ``--enable-verify`` does name one. The picture
shows the model as written; the machine that runs is not what a reader needs to
see. No output marks the current configuration of a run: a runtime overlay is not
part of what these outputs do.

How the order is guaranteed
---------------------------

The regions of one owner have no transitions between them, so a layout engine
has nothing to keep them in order. ELK, which lays out the viewer and the
preview, is free to move them to reduce edge crossings, and it does: a model
with regions A, B and C came back as C, A, B. Its own ordering options either
do nothing for the nested layout the renderer uses or crash it, so the order is
not requested from the engine. It is restored afterwards.

.. list-table:: The layout steps for regions
   :header-rows: 1
   :widths: 6 40 54

   * - Step
     - What happens
     - Why it is safe
   * - 1
     - ELK lays out the whole graph.
     - Positions come from the engine; the order of regions is whatever it chose.
   * - 2
     - The regions of each owner are sorted by ``ordinal`` and put back, one
       after another, into the slots the engine produced, keeping each region's
       size and the gaps between them.
     - A region is connected to nothing outside itself, so moving it sideways
       cannot disturb an edge, and the owner keeps its size.
   * - 3
     - If the regions of an owner do not sit on one row (one column in a
       left-to-right diagram), the graph is laid out again with a chain of
       invisible edges between consecutive regions, which pins the order.
     - It costs a longer diagram, and only in that case. The renderer skips
       those edges (``kind`` ``regionOrder``).
   * - 4
     - The regions are tiled over the owner's body, with a dashed divider
       between neighbours.
     - Same last step on both paths, so the picture looks the same whether or
       not step 3 ran.

The order runs along the diagram's direction: left to right within one row in a
top-to-bottom diagram, and top to bottom within one column in a left-to-right
diagram. The HTML viewer and the VS Code preview call the same layout function,
so they cannot disagree about it. PlantUML does not use this code at all: pyfcstm
hands it the partitions in writing order, as the output above shows, and PlantUML
lays out the rest.

Four surfaces, one set of conventions
-------------------------------------

The four ways of looking at a model share conventions and nothing else.

.. list-table:: The surfaces and what each one limits
   :header-rows: 1
   :widths: 22 26 52

   * - Surface
     - Entry point
     - What is specific to it
   * - PlantUML text
     - ``pyfcstm plantuml``
     - Text that goes under version control. Layout is done by PlantUML, not by
       pyfcstm. PlantUML's built-in Smetana layout does not support concurrent
       partitions and drops every region after the first one; pyfcstm emits no
       layout directive, so you meet this only when you force that layout. Use the
       default Graphviz layout.
   * - Diagram snapshot
     - ``StateMachine.diagram()``, ``pyfcstm diagram``
     - Portable data with no layout. It is detached from the model, so editing
       the model afterwards does not change it.
   * - HTML viewer
     - ``Diagram.to_html`` / ``save`` / ``show``, ``pyfcstm diagram -o x.html`` /
       ``--open``
     - One self-contained file that lays out with ELK and the reordering above;
       ``--open`` needs a Chromium-family browser and blocks.
   * - VS Code preview
     - The editor extension
     - The same layout function, driven by the editor's own model of the open
       document instead of a snapshot from Python.

The shared conventions are the ones above: ``region N: Name`` with ``N`` the
writing order, ``active("...")`` shown as written, no hidden variables, and a
region counting as one layer for ``max_depth``. They are shared because a reader
moves between these surfaces for one model; a difference in convention would
look like a difference in the model.

Known gaps in what regions look like, none of which changes what the model does:

* A collapsed region keeps the size it had when expanded; the owner does not
  shrink around it.
* The editor supports regions in three ways besides the preview: it reports
  ``E_REGION_STRUCTURE``, ``E_DUPLICATE_REGION`` and ``E_ACTIVE_QUERY_TARGET``,
  it folds ``region`` blocks and it formats them. What it does not have is
  region-specific handling in symbols (outline and breadcrumbs), hover,
  references and rename: the code behind those features has no region case, and
  the recorded behaviour is that a region shows up like a state, its details say
  ``composite``, renaming a state does not update ``active("...")`` strings that
  name it, and hovering shows nothing. The recorded behaviour was not re-checked in
  a running editor while writing this page.
* A model that uses history is drawn as written by PlantUML and by the Python
  snapshot, and the editor preview still draws the expanded machine; see
  `issue #590 <https://github.com/HansBug/pyfcstm/issues/590>`_.
* The title width is estimated, not measured, so a region name of about fifty
  characters can push the end of its title onto the collapse button by a pixel
  or two.

Next steps
----------

Use :doc:`/how_to/visualization/index` for the tasks, and
:doc:`/reference/visualization_options/index` for the exact option fields, environment
variables, and behaviour boundaries this page reasons about.
