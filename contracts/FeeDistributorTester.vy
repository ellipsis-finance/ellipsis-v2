# @version 0.3.0

from vyper.interfaces import ERC20

owner: public(address)


@external
def __init__():
    self.owner = msg.sender


@external
def depositFee(_token: address, _amount: uint256) -> bool:
    ERC20(_token).transferFrom(msg.sender, self, _amount)
    return True


@external
def transfer(_token: address, _receiver: address, _amount: uint256):
    assert msg.sender == self.owner
    ERC20(_token).transfer(_receiver, _amount)
