# @version 0.3.0

from vyper.interfaces import ERC20

@external
def depositFee(_token: address, _amount: uint256) -> bool:
    ERC20(_token).transferFrom(msg.sender, self, _amount)
    return True
