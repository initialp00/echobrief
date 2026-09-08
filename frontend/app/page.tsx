import { BriefForm } from "@/components/BriefForm";
import { BriefList } from "@/components/BriefList";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function DashboardPage() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Submit a brief</CardTitle>
          <CardDescription>
            Record a 30–90s incident update as a transcript or audio URL. It is
            processed asynchronously through the pipeline.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <BriefForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent briefs</CardTitle>
          <CardDescription>
            Live status of the last 20 briefs. Click one to watch its pipeline.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <BriefList />
        </CardContent>
      </Card>
    </div>
  );
}
