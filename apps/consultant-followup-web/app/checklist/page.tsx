import { DemoWorkspace } from "@/components/demo-workspace";

export default function ChecklistPage() {
  return (
    <main className="page-shell app-main">
      <DemoWorkspace forcedView="checklist" useIndividualPages />
    </main>
  );
}
