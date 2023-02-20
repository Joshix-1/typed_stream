# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Java-like typed Stream class for easier handling of generators."""

from .exceptions import StreamEmptyError, StreamFinishedError
from .streamable import Streamable, StreamableSequence
from .streams import BinaryFileStream, FileStream, Stream
from .version import VERSION

__version__ = VERSION
__all__ = (
    "BinaryFileStream",
    "FileStream",
    "Stream",
    "StreamEmptyError",
    "StreamFinishedError",
    "Streamable",
    "StreamableSequence",
    "VERSION",
)
