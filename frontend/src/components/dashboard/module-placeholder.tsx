import { Construction } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function ModulePlaceholder({
  title,
  description,
  phase,
}: {
  title: string;
  description: string;
  phase: string;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{title}</h1>
        <p className="text-muted-foreground">{description}</p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <Construction className="h-10 w-10 text-primary" />
          <p className="font-medium">Coming in {phase}</p>
          <p className="max-w-md text-sm text-muted-foreground">
            The data model and APIs for this module are designed and migrated. The interface
            is delivered in {phase} of the roadmap.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
