// Pre-rendered organization AST graph and contracts for cloud resilience (e.g., AWS Amplify)
export const DEFAULT_NODES: any[] = [
  {
    "id": "RUXAILAB:i18n-diff-guard.mjs:gitDiff:18",
    "label": "gitDiff",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "i18n-diff-guard.mjs",
    "start_line": 18,
    "end_line": 24,
    "signature": "function gitDiff(args) {",
    "docstring": "",
    "x": 1020,
    "y": 70
  },
  {
    "id": "RUXAILAB:i18n-diff-guard.mjs:getDiff:26",
    "label": "getDiff",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "i18n-diff-guard.mjs",
    "start_line": 26,
    "end_line": 37,
    "signature": "function getDiff() {",
    "docstring": "",
    "x": 1020,
    "y": 122
  },
  {
    "id": "RUXAILAB:i18n-diff-guard.mjs:loadLocale:94",
    "label": "loadLocale",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "i18n-diff-guard.mjs",
    "start_line": 94,
    "end_line": 102,
    "signature": "function loadLocale(locale) {",
    "docstring": "",
    "x": 1020,
    "y": 174
  },
  {
    "id": "RUXAILAB:i18n-diff-guard.mjs:hasKey:104",
    "label": "hasKey",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "i18n-diff-guard.mjs",
    "start_line": 104,
    "end_line": 112,
    "signature": "function hasKey(obj, key) {",
    "docstring": "",
    "x": 1020,
    "y": 226
  },
  {
    "id": "RUXAILAB:sonarcloud_to_github.py:Config:17",
    "label": "Config",
    "repo": "RUXAILAB",
    "kind": "class",
    "file_path": "sonarcloud_to_github.py",
    "start_line": 17,
    "end_line": 37,
    "signature": "class Config:",
    "docstring": "Configuration class for the integration",
    "x": 1020,
    "y": 278
  },
  {
    "id": "RUXAILAB:sonarcloud_to_github.py:get_sonarcloud_issues:39",
    "label": "get_sonarcloud_issues",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "sonarcloud_to_github.py",
    "start_line": 39,
    "end_line": 87,
    "signature": "def get_sonarcloud_issues() -> List[Dict[str, Any]]:",
    "docstring": "Fetch new issues from SonarCloud.\nReturns:\n    List of SonarCloud issues.",
    "x": 1020,
    "y": 330
  },
  {
    "id": "RUXAILAB:sonarcloud_to_github.py:get_existing_github_issues:89",
    "label": "get_existing_github_issues",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "sonarcloud_to_github.py",
    "start_line": 89,
    "end_line": 134,
    "signature": "def get_existing_github_issues() -> Dict[str, Any]:",
    "docstring": "Get existing Github issues to check for duplicates.\nReturns:\n    Dict mapping SonarCloud issue keys to GitHub issue data.",
    "x": 1020,
    "y": 382
  },
  {
    "id": "RUXAILAB:sonarcloud_to_github.py:get_next_github_issue_number:136",
    "label": "get_next_github_issue_number",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "sonarcloud_to_github.py",
    "start_line": 136,
    "end_line": 181,
    "signature": "def get_next_github_issue_number() -> int:",
    "docstring": "Get the next GitHub issue number by finding the highest current issue number\n\nReturns:\n    int: The next issue number (current highest + 1)",
    "x": 1020,
    "y": 434
  },
  {
    "id": "RUXAILAB:sonarcloud_to_github.py:create_github_issue:183",
    "label": "create_github_issue",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "sonarcloud_to_github.py",
    "start_line": 183,
    "end_line": 258,
    "signature": "def create_github_issue(issue: Dict[str, Any], next_number: int) -> Tuple[bool, int]:",
    "docstring": "Create a Github issue from a SonarCloud issue\n\nArgs:\n    issue: SonarCloud issue data\n    next_number: Expected issue number to include in the title\n    \nReturns:\n    Tuple[bool, int]: Success status and actual issue number",
    "x": 1020,
    "y": 486
  },
  {
    "id": "RUXAILAB:sonarcloud_to_github.py:should_create_issue:260",
    "label": "should_create_issue",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "sonarcloud_to_github.py",
    "start_line": 260,
    "end_line": 278,
    "signature": "def should_create_issue(issue: Dict[str, Any], existing_issues: Dict[str, Any]) -> bool:",
    "docstring": "Determine if an issue should trigger GitHub issue creation\n\nArgs:\n    issue: SonarCloud issue data\n    existing_issues: Dictionary of existing GitHub issues keyed by SonarCloud issue key\n    \nReturns:\n    bool: True if issue should be created, False otherwise",
    "x": 1020,
    "y": 538
  },
  {
    "id": "RUXAILAB:sonarcloud_to_github.py:check_prerequisites:280",
    "label": "check_prerequisites",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "sonarcloud_to_github.py",
    "start_line": 280,
    "end_line": 298,
    "signature": "def check_prerequisites() -> bool:",
    "docstring": "Check if all require environment variables are set\n\nReturns:\n    bool: True if all prerequisites are met, else False",
    "x": 1020,
    "y": 590
  },
  {
    "id": "RUXAILAB:sonarcloud_to_github.py:main:300",
    "label": "main",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "sonarcloud_to_github.py",
    "start_line": 300,
    "end_line": 349,
    "signature": "def main() -> None:",
    "docstring": "Main function to fetch issues from SonarCloud and create issues on Github",
    "x": 1020,
    "y": 642
  },
  {
    "id": "RUXAILAB:tests/test-utils.js:render:26",
    "label": "render",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/test-utils.js",
    "start_line": 26,
    "end_line": 26,
    "signature": "export function render(component, options = {}, { customStore } = {}) {",
    "docstring": "",
    "x": 1020,
    "y": 694
  },
  {
    "id": "RUXAILAB:tests/test-utils.js:renderWithMockStore:38",
    "label": "renderWithMockStore",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/test-utils.js",
    "start_line": 38,
    "end_line": 38,
    "signature": "export function renderWithMockStore(component, options = {}) {",
    "docstring": "",
    "x": 1020,
    "y": 746
  },
  {
    "id": "RUXAILAB:tests/unit/cooperatorInviteValidation.spec.js:t:6",
    "label": "t",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/cooperatorInviteValidation.spec.js",
    "start_line": 6,
    "end_line": 20,
    "signature": "const t = (key) => {",
    "docstring": "",
    "x": 1020,
    "y": 798
  },
  {
    "id": "RUXAILAB:tests/unit/ReportController.spec.js:and:79",
    "label": "and",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/ReportController.spec.js",
    "start_line": 79,
    "end_line": 90,
    "signature": "it('should use taskAnswers for USER test type and cascade transcriptions', async () => {",
    "docstring": "",
    "x": 1020,
    "y": 850
  },
  {
    "id": "RUXAILAB:tests/unit/ReportController.spec.js:setupMocks:63",
    "label": "setupMocks",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/ReportController.spec.js",
    "start_line": 63,
    "end_line": 68,
    "signature": "const setupMocks = (userExists = true, answerExists = true) => {",
    "docstring": "",
    "x": 1020,
    "y": 902
  },
  {
    "id": "RUXAILAB:tests/unit/TranscriptionController.spec.js:toFirestore:19",
    "label": "toFirestore",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/TranscriptionController.spec.js",
    "start_line": 19,
    "end_line": 21,
    "signature": "toFirestore() {",
    "docstring": "",
    "x": 1020,
    "y": 954
  },
  {
    "id": "RUXAILAB:tests/unit/screenShareCapture.spec.js:mockMediaDevices:13",
    "label": "mockMediaDevices",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/screenShareCapture.spec.js",
    "start_line": 13,
    "end_line": 20,
    "signature": "function mockMediaDevices(getDisplayMedia) {",
    "docstring": "",
    "x": 1020,
    "y": 1006
  },
  {
    "id": "RUXAILAB:tests/unit/screenShareCapture.spec.js:createStream:22",
    "label": "createStream",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/screenShareCapture.spec.js",
    "start_line": 22,
    "end_line": 22,
    "signature": "function createStream(displaySurface, { stop = jest.fn() } = {}) {",
    "docstring": "",
    "x": 1020,
    "y": 1058
  },
  {
    "id": "RUXAILAB:tests/unit/consentDeclineRoomWipe.spec.js:dbRef:11",
    "label": "dbRef",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/consentDeclineRoomWipe.spec.js",
    "start_line": 11,
    "end_line": 11,
    "signature": "const dbRef = (db, path) => ({ path })",
    "docstring": "",
    "x": 1020,
    "y": 1110
  },
  {
    "id": "RUXAILAB:tests/unit/consentDeclineRoomWipe.spec.js:set:12",
    "label": "set",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/consentDeclineRoomWipe.spec.js",
    "start_line": 12,
    "end_line": 26,
    "signature": "const set = async (ref, val) => {",
    "docstring": "",
    "x": 1020,
    "y": 1162
  },
  {
    "id": "RUXAILAB:tests/unit/consentDeclineRoomWipe.spec.js:onValue:28",
    "label": "onValue",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/consentDeclineRoomWipe.spec.js",
    "start_line": 28,
    "end_line": 36,
    "signature": "const onValue = (ref, callback) => {",
    "docstring": "",
    "x": 1020,
    "y": 1214
  },
  {
    "id": "RUXAILAB:tests/unit/consentDeclineRoomWipe.spec.js:initModeratedSession:38",
    "label": "initModeratedSession",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/consentDeclineRoomWipe.spec.js",
    "start_line": 38,
    "end_line": 76,
    "signature": "const initModeratedSession = async () => {",
    "docstring": "",
    "x": 1020,
    "y": 1266
  },
  {
    "id": "RUXAILAB:tests/unit/consentDeclineRoomWipe.spec.js:createPresence:52",
    "label": "createPresence",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/consentDeclineRoomWipe.spec.js",
    "start_line": 52,
    "end_line": 53,
    "signature": "const createPresence = (id, name) =>",
    "docstring": "",
    "x": 1020,
    "y": 1318
  },
  {
    "id": "RUXAILAB:tests/unit/auditTrailDisplay.spec.js:t:22",
    "label": "t",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/auditTrailDisplay.spec.js",
    "start_line": 22,
    "end_line": 22,
    "signature": "const t = (key, params = {}) =>",
    "docstring": "",
    "x": 1020,
    "y": 1370
  },
  {
    "id": "RUXAILAB:tests/unit/auditTrailDisplay.spec.js:te:28",
    "label": "te",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/auditTrailDisplay.spec.js",
    "start_line": 28,
    "end_line": 96,
    "signature": "const te = (key) => key in translations",
    "docstring": "",
    "x": 1020,
    "y": 1422
  },
  {
    "id": "RUXAILAB:tests/unit/AuditTrailView.spec.js:mountView:57",
    "label": "mountView",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/AuditTrailView.spec.js",
    "start_line": 57,
    "end_line": 85,
    "signature": "const mountView = () =>",
    "docstring": "",
    "x": 1020,
    "y": 1474
  },
  {
    "id": "RUXAILAB:tests/unit/studyLoggingClient.spec.js:createQueueStore:7",
    "label": "createQueueStore",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/studyLoggingClient.spec.js",
    "start_line": 7,
    "end_line": 41,
    "signature": "const createQueueStore = () => {",
    "docstring": "",
    "x": 1020,
    "y": 1526
  },
  {
    "id": "RUXAILAB:tests/unit/studyLoggingClient.spec.js:mutate:11",
    "label": "mutate",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/studyLoggingClient.spec.js",
    "start_line": 11,
    "end_line": 23,
    "signature": "mutate(key, change) {",
    "docstring": "",
    "x": 1020,
    "y": 1578
  },
  {
    "id": "RUXAILAB:tests/unit/studyLoggingClient.spec.js:cleanupOwner:24",
    "label": "cleanupOwner",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/studyLoggingClient.spec.js",
    "start_line": 24,
    "end_line": 29,
    "signature": "cleanupOwner(ownerUid) {",
    "docstring": "",
    "x": 1020,
    "y": 1630
  },
  {
    "id": "RUXAILAB:tests/unit/studyLoggingClient.spec.js:sweepExpired:30",
    "label": "sweepExpired",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/studyLoggingClient.spec.js",
    "start_line": 30,
    "end_line": 39,
    "signature": "sweepExpired(now) {",
    "docstring": "",
    "x": 1020,
    "y": 1682
  },
  {
    "id": "RUXAILAB:tests/unit/TestView.spec.js:mountTestView:40",
    "label": "mountTestView",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/TestView.spec.js",
    "start_line": 40,
    "end_line": 40,
    "signature": "const mountTestView = ({ store, router, route, props = {} }) =>",
    "docstring": "",
    "x": 1020,
    "y": 1734
  },
  {
    "id": "RUXAILAB:tests/unit/HeuristicAIAgents.spec.js:html:35",
    "label": "html",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/HeuristicAIAgents.spec.js",
    "start_line": 35,
    "end_line": 51,
    "signature": "<!doctype html><html lang=\"en\"><head><title>Example</title></head>",
    "docstring": "",
    "x": 1020,
    "y": 1786
  },
  {
    "id": "RUXAILAB:tests/unit/studyAccessPolicy.spec.js:userStudy:21",
    "label": "userStudy",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/studyAccessPolicy.spec.js",
    "start_line": 21,
    "end_line": 21,
    "signature": "const userStudy = (overrides = {}) => ({",
    "docstring": "",
    "x": 1020,
    "y": 1838
  },
  {
    "id": "RUXAILAB:tests/unit/studySummaryExport.spec.js:studyFor:4",
    "label": "studyFor",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/studySummaryExport.spec.js",
    "start_line": 4,
    "end_line": 11,
    "signature": "const studyFor = (userId, role) => ({",
    "docstring": "",
    "x": 1020,
    "y": 1890
  },
  {
    "id": "RUXAILAB:tests/unit/breakoutGroups.spec.js:baseGroups:65",
    "label": "baseGroups",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/breakoutGroups.spec.js",
    "start_line": 65,
    "end_line": 68,
    "signature": "const baseGroups = () => ({",
    "docstring": "",
    "x": 1020,
    "y": 1942
  },
  {
    "id": "RUXAILAB:tests/unit/HeuristicTestView.spec.js:deferred:57",
    "label": "deferred",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/HeuristicTestView.spec.js",
    "start_line": 57,
    "end_line": 63,
    "signature": "const deferred = () => {",
    "docstring": "",
    "x": 1020,
    "y": 1994
  },
  {
    "id": "RUXAILAB:tests/unit/HeuristicTestView.spec.js:findButton:72",
    "label": "findButton",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/HeuristicTestView.spec.js",
    "start_line": 72,
    "end_line": 389,
    "signature": "const findButton = (wrapper, text) =>",
    "docstring": "",
    "x": 1020,
    "y": 2046
  },
  {
    "id": "RUXAILAB:tests/unit/studyNavigation.spec.js:to:323",
    "label": "to",
    "repo": "RUXAILAB",
    "kind": "function",
    "file_path": "tests/unit/studyNavigation.spec.js",
    "start_line": 323,
    "end_line": 337,
    "signature": "it('maps each study type to the route base used by manager fallbacks', () => {",
    "docstring": "",
    "x": 1020,
    "y": 2098
  }
];

export const DEFAULT_EDGES: any[] = [
  {
    "from": "web-eye-tracker-front:src/store/calibration.js:sendData:328",
    "to": "eye-tracker-api:app/main.py:calib_validation:24",
    "kind": "http",
    "edge_type": "consumes_api"
  },
  {
    "from": "RUXAILAB:sonarcloud_to_github.py:main:300",
    "to": "RUXAILAB:sonarcloud_to_github.py:check_prerequisites:280",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:sonarcloud_to_github.py:main:300",
    "to": "RUXAILAB:sonarcloud_to_github.py:create_github_issue:183",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:sonarcloud_to_github.py:main:300",
    "to": "RUXAILAB:sonarcloud_to_github.py:get_existing_github_issues:89",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:sonarcloud_to_github.py:main:300",
    "to": "RUXAILAB:sonarcloud_to_github.py:get_next_github_issue_number:136",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:sonarcloud_to_github.py:main:300",
    "to": "RUXAILAB:sonarcloud_to_github.py:get_sonarcloud_issues:39",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:sonarcloud_to_github.py:main:300",
    "to": "RUXAILAB:sonarcloud_to_github.py:should_create_issue:260",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/main.py:fill_ahp_matrix:164",
    "to": "RUXAILAB:weight_function/main.py:generate_saaty_scale_with_explanations:130",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/main.py:populate_ahp_matrix:195",
    "to": "RUXAILAB:weight_function/main.py:fill_ahp_matrix:164",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/main.py:populate_ahp_matrix:195",
    "to": "RUXAILAB:weight_function/main.py:generate_saaty_scale_with_explanations:130",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/main.py:weight_calculate:276",
    "to": "RUXAILAB:weight_function/main.py:calculate_eigen:29",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/main.py:weight_calculate:276",
    "to": "RUXAILAB:weight_function/main.py:initialize_ahp_matrix:97",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/main.py:weight_calculate:276",
    "to": "RUXAILAB:weight_function/main.py:populate_ahp_matrix:195",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestCalculateEigen:18",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_calculate_eigen_consistency:21",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestCalculateEigen:18",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_calculate_eigen_consistency:21",
    "kind": "calls",
    "edge_type": "defines"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestCalculateEigen:18",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_calculate_eigen_output_shape:44",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestCalculateEigen:18",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_calculate_eigen_output_shape:44",
    "kind": "calls",
    "edge_type": "defines"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestCalculateEigen:18",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_calculate_eigen_small_matrix:60",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestCalculateEigen:18",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_calculate_eigen_small_matrix:60",
    "kind": "calls",
    "edge_type": "defines"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestCalculateEigen:18",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_consistency_interpretation_message:75",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestCalculateEigen:18",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_consistency_interpretation_message:75",
    "kind": "calls",
    "edge_type": "defines"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestInitializeAhpMatrix:86",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_initialize_ahp_matrix_initialization:100",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestInitializeAhpMatrix:86",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_initialize_ahp_matrix_initialization:100",
    "kind": "calls",
    "edge_type": "defines"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestInitializeAhpMatrix:86",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_initialize_ahp_matrix_labels:111",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestInitializeAhpMatrix:86",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_initialize_ahp_matrix_labels:111",
    "kind": "calls",
    "edge_type": "defines"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestInitializeAhpMatrix:86",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_initialize_ahp_matrix_shape:89",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main.py:TestInitializeAhpMatrix:86",
    "to": "RUXAILAB:weight_function/tests/test_main.py:test_initialize_ahp_matrix_shape:89",
    "kind": "calls",
    "edge_type": "defines"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main_extended.py:TestFillAhpMatrix:71",
    "to": "RUXAILAB:weight_function/tests/test_main_extended.py:setUp:134",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main_extended.py:TestFillAhpMatrix:71",
    "to": "RUXAILAB:weight_function/tests/test_main_extended.py:setUp:74",
    "kind": "calls",
    "edge_type": "defines"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main_extended.py:TestFillAhpMatrix:71",
    "to": "RUXAILAB:weight_function/tests/test_main_extended.py:test_fill_ahp_matrix_equal_importance:115",
    "kind": "calls",
    "edge_type": "calls"
  },
  {
    "from": "RUXAILAB:weight_function/tests/test_main_extended.py:TestFillAhpMatrix:71",
    "to": "RUXAILAB:weight_function/tests/test_main_extended.py:test_fill_ahp_matrix_equal_importance:115",
    "kind": "calls",
    "edge_type": "defines"
  }
];

export const DEFAULT_STATS = {
  repositories: [
    'web-eye-tracker-front',
    'eye-tracker-api',
    'sentiment-analysis-api',
    'RUXAILAB',
    'facial-sentiment-analysis-api'
  ],
  total_symbols: 1578,
  total_edges: 365,
  cross_repo_edges: 1,
  db_engine: 'AWS OpenSearch Serverless',
  runtime_env: 'aws',
  aws: {
    connected: true,
    mode: 'aws_bedrock_live',
    region: 'us-west-2',
    active_model: 'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
    embedding_model: 'amazon.titan-embed-text-v2:0'
  }
};
