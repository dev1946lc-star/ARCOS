import hre from "hardhat";

async function main() {
  console.log("Deploying NanoPayment contract...");

  const NanoPayment = await hre.ethers.getContractFactory("NanoPayment");
  const nanoPayment = await NanoPayment.deploy();

  await nanoPayment.waitForDeployment();

  const address = await nanoPayment.getAddress();
  console.log(`NanoPayment deployed to: ${address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
