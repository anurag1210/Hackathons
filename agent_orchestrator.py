#Agent Orchestrator.py file to Orchestrate the entire Agent Framework to call all the differnt functionality
import click
import pandas as pd
from scraper import build_corpus as run_build_corpus
from retriever import init_vectorstore
from pipeline import run_pipeline


@click.command()
@click.option("--input","input_path",required=True,type=click.Path(exists=True, dir_okay=False),help="Path to the input tickets CSV.")
@click.option("--output","output_path",required=True,type=click.Path(dir_okay=False),help="Path to write the results CSV.")
@click.option("--build-corpus", is_flag=True,help="Scrape and rebuild the vectorstore before processing tickets.")
@click.option("--verbose",is_flag=True,help="Enable detailed per-ticket logging.")

def main(input_path, output_path, build_corpus, verbose):
    """Run the support ticket agent orchestrator."""

    click.echo("Starting agent orchestrator...")
    click.echo(f"Input CSV: {input_path}")
    click.echo(f"Output CSV: {output_path}")
    click.echo(f"Build corpus: {build_corpus}")
    click.echo(f"Verbose: {verbose}")

    if build_corpus:
        click.echo("[*] Building corpus...")
        run_build_corpus()

    if verbose:
        click.echo("Verbose logging enabled.")

    # Call your actual orchestration logic here
    # process_tickets(input_path, output_path, build_corpus, verbose)

    #Pandas Read and handling the input sample support tickets csv file
    #Issue,Subject,Company
    df = pd.read_csv(input_path)
    df['Company']=df["Company"].fillna("unknown").str.strip().str.lower()
    df["Company"] = df["Company"].replace("none", "unknown")
    
    click.echo("[*] Initialising vectorstore...")
    vectorstore = init_vectorstore(build_corpus=build_corpus)

    results = []

    total_tickets = len(df)

    for i, (idx, row) in enumerate(df.iterrows(), start=1):
        click.echo(f"[{i}/{total_tickets}] Processing...")

        try:
            result = run_pipeline(row, vectorstore, verbose=verbose)
            results.append(result)

            if verbose:
                click.echo(f"[verbose] Result: {result}")

        except Exception as e:
            error_result = {
                "status": "escalated",
                "product_area": "unknown",
                "response": f"Pipeline failed for this ticket: {str(e)}",
                "justification": "Exception occurred during pipeline execution.",
                "request_type": "invalid",
            }
            results.append(error_result)
            click.echo(f"[error] Ticket {i} failed: {e}")

    results_df = pd.DataFrame(results)
    results_df.to_csv(output_path, index=False)

    click.echo(f"[*] Wrote {len(results_df)} results to {output_path}")

if __name__=="__main__":
     main()