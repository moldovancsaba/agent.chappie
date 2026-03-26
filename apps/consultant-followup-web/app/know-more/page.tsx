import { DemoWorkspace } from "@/components/demo-workspace";

export default function KnowMorePage() {
  return (
    <main className="page-shell app-main">
      <DemoWorkspace forcedView="know-more" useIndividualPages />
    </main>
  );
}
