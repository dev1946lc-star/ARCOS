import hre from "hardhat";

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log(`Deploying contracts with the account: ${deployer.address}`);

  // Deploy MockUSDC
  console.log("Deploying MockUSDC...");
  const MockUSDC = await hre.ethers.getContractFactory("MockUSDC");
  const mockUSDC = await MockUSDC.deploy();
  await mockUSDC.waitForDeployment();
  const usdcAddress = await mockUSDC.getAddress();
  console.log(`MockUSDC deployed to: ${usdcAddress}`);

  // Deploy AgentEscrowUSDC
  console.log("Deploying AgentEscrowUSDC...");
  const AgentEscrowUSDC = await hre.ethers.getContractFactory("AgentEscrowUSDC");
  const agentEscrow = await AgentEscrowUSDC.deploy(usdcAddress);
  await agentEscrow.waitForDeployment();
  const escrowAddress = await agentEscrow.getAddress();
  console.log(`AgentEscrowUSDC deployed to: ${escrowAddress}`);

  // Deploy NanoPayment
  console.log("Deploying NanoPayment...");
  const NanoPayment = await hre.ethers.getContractFactory("NanoPayment");
  const nanoPayment = await NanoPayment.deploy();
  await nanoPayment.waitForDeployment();
  const nanoPaymentAddress = await nanoPayment.getAddress();
  console.log(`NanoPayment deployed to: ${nanoPaymentAddress}`);

  console.log("\nSummary of deployed addresses:");
  console.log(`MockUSDC: ${usdcAddress}`);
  console.log(`AgentEscrowUSDC: ${escrowAddress}`);
  console.log(`NanoPayment: ${nanoPaymentAddress}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
