import { DemoWorkspace } from "@/components/demo-workspace";

export default function SourcesJobsPage() {
  return (
    <main className="page-shell app-main">
      <DemoWorkspace forcedView="sources-jobs" useIndividualPages />
    </main>
  );
}
