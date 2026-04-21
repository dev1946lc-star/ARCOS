import "@nomicfoundation/hardhat-toolbox";

/** @type import('hardhat/config').HardhatUserConfig */
export default {
  solidity: "0.8.20",
  networks: {
    arc: {
      url: process.env.ARC_RPC_URL || "http://127.0.0.1:8545",
      accounts: process.env.ARC_DEPLOYER_PRIVATE_KEY ? [process.env.ARC_DEPLOYER_PRIVATE_KEY] : [],
    },
  },
};
