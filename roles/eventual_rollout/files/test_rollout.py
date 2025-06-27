import unittest
from unittest.mock import MagicMock

from rollout import rollout

class TestRollout(unittest.TestCase):
    def test_rollout_all_vms_eventually_not_busy(self):
        ghc = MagicMock()
        org = MagicMock()
        ghc.get_organization.return_value = org

        vms = {"vm1", "vm2"}

        # Internal state to track calls count
        call_count = {"count": 0}

        def get_self_hosted_runners():
            # After 2 calls, runners become not busy (False)
            busy_status = call_count["count"] < 2  # True for first 2 calls, then False
            call_count["count"] += 1

            # Return runner mocks
            return [MagicMock(name=vm, busy=busy_status) for vm in vms]

        org.get_self_hosted_runners.side_effect = get_self_hosted_runners
        org.delete_self_hosted_runner = MagicMock()

        vmm = MagicMock()
        vmm.deploy = MagicMock()
        vmm.destroy = MagicMock()

        result = rollout(ghc, vms, "org_name", vmm)
        print(result)
        self.assertIn("completed", result)

if __name__ == "__main__":
    unittest.main()

