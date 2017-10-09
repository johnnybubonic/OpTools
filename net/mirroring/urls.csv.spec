"UUID","URL","SHA512_of_CONTENT","LAST_FETCHED_IN_UNIX_EPOCH"

UUID can be any non-whitespace, non-slashed string suitable for filenames you want, but I recommend a UUID4.
You can generate one at either https://www.uuidgenerator.net/ or via python:

>>> import uuid
>>> str(uuid.uuid4())
'16728c9e-5fde-4f63-8a36-4a3db612be8d'

It should be unique for every page.


You can generate an UNIX Epoch timestamp via:

  date '+%s'
