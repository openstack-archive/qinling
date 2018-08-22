#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Set work dir if not already done
: ${WORK_DIR:="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"}

# Get Host OS
source /etc/os-release
export HOST_OS=${HOST_OS:="${ID}"}

# Set Upstream DNS
export UPSTREAM_DNS=${UPSTREAM_DNS:-"8.8.8.8"}
