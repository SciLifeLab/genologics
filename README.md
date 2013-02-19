## Python interface to the GenoLogics LIMS server via its REST API.

A basic module for interacting with the GenoLogics LIMS server via
its REST API. The goal is to provide simple access to the most common
entities and their attributes in a reasonably Pythonic fashion.

### Design

All instances of Project, Sample, Artifact, etc should be obtained using
the get_* methods of the Lims class, which keeps an internal cache of
current instances. The idea is to create one and only one instance in
a running script for representing an item in the database. If one has
more than one instance representing the same item, there is a danger that
one of them gets updated and not the others.

An instance of Project, Sample, Artifact, etc, retrieves lazily (i.e.
only when required) its XML representation from the database. This
is parsed and kept as an ElementTree within the instance. All access
to predefined attributes goes via descriptors which read from or
modify the ElementTree. This simplifies writing back an updated
instance to the database.

### Installation

```
pip install genologics
```

or for the cutting edge version:

```
pip install https://github.com/SciLifeLab/genologics/tarball/master
```

### Usage

The URL and credentials should be wrintten in a new file in any
of those config files (ordered by preference):

```
$HOME/.genologicsrc, .genologicsrc, genologics.conf, genologics.cfg
```

or if installed system_wide:

```
/etc/genologics.conf
```

```
[genologics]
BASEURI=https://yourlims.example.com:8443
USERNAME=your_username
PASSWORD=your_password
```

### Example scripts

Usage example scripts are provided in the subdirectory 'examples'.

NOTE: The example files rely on specific entities and configurations
on the server, and use base URI, user name and password, so to work
for your server, all these must be reviewed and modified.

### Known bugs 

- Artifact state is part of its URL (as a query parameter).
  It is not entirely clear how to deal with this in the Lims.cache:
  Currently, an artifact that has the current state may be represented
  by a URL that includes the state, and another that does not contain it.
