import click
import camelot


@click.group()
def main():
    pass


@main.command()
@click.argument('path', type = str)
def extract_tables(path: str):
    tables = camelot.read_pdf(path)

    print(tables)


if __name__ == '__main__':
    main()
