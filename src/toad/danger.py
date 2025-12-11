from enum import IntEnum
from pathlib import Path
from typing import Iterable, NamedTuple


SAFE_COMMANDS = {
    # Display & Output
    "echo",
    "cat",
    "less",
    "more",
    "head",
    "tail",
    "tac",
    "nl",
    # File & Directory Information
    "ls",
    "tree",
    "pwd",
    "file",
    "stat",
    "du",
    "df",
    # Search & Find
    "find",
    "locate",
    "which",
    "whereis",
    "type",
    "grep",
    "egrep",
    "fgrep",
    # Text Processing (read-only)
    "wc",
    "sort",
    "uniq",
    "cut",
    "paste",
    "column",
    "tr",
    "diff",
    "cmp",
    "comm",
    # System Information
    "whoami",
    "who",
    "w",
    "id",
    "hostname",
    "uname",
    "uptime",
    "date",
    "cal",
    "env",
    "printenv",
    # Process Information
    "ps",
    "top",
    "htop",
    "pgrep",
    "jobs",
    "pstree",
    # Network (read-only operations)
    "ping",
    "traceroute",
    "nslookup",
    "dig",
    "host",
    "netstat",
    "ss",
    "ifconfig",
    "ip",
    # View compressed files (without extracting)
    "zcat",
    "zless",
    # History & Help
    "history",
    "man",
    "help",
    "info",
    "apropos",
    "whatis",
    # Comparison & Checksums
    "md5sum",
    "sha256sum",
    "sha1sum",
    "cksum",
    "sum",
    # Other Safe Commands
    "bc",
    "expr",
    "test",
    "sleep",
    "true",
    "false",
    "yes",
    "seq",
    "basename",
    "dirname",
    "realpath",
    "readlink",
}

UNSAFE_COMMANDS = {
    # File/Directory Creation
    "mkdir",
    "touch",
    "mktemp",
    "mkfifo",
    "mknod",
    # File/Directory Deletion
    "rm",
    "rmdir",
    "shred",
    # File/Directory Moving/Copying
    "mv",
    "cp",
    "rsync",
    "scp",
    "install",
    # File Modification/Editing
    "vi",
    "vim",
    "nvim",
    "nano",
    "emacs",
    "ed",
    "pico",
    "gedit",
    "sed",  # with -i flag
    "awk",  # can write files
    "tee",  # writes to files and stdout
    # Permissions/Ownership
    "chmod",
    "chown",
    "chgrp",
    "chattr",
    "setfacl",
    # Linking
    "ln",
    "link",
    "unlink",
    # Archive/Compression (extract/compress operations)
    "tar",
    "untar",
    "zip",
    "unzip",
    "gzip",
    "gunzip",
    "bzip2",
    "bunzip2",
    "xz",
    "unxz",
    "7z",
    "rar",
    "unrar",
    # Download Tools
    "wget",
    "curl",
    "fetch",
    "aria2c",
    # Low-level Disk Operations
    "dd",
    "truncate",
    "fallocate",
    # File Splitting
    "split",
    "csplit",
    # Synchronization
    "sync",
    # Package Managers (install/modify software)
    "apt",
    "apt-get",
    "yum",
    "dnf",
    "pacman",
    "zypper",
    "brew",
    "pip",
    "pip3",
    "npm",
    "yarn",
    "gem",
    "cargo",
    # Build/Compilation Tools
    "make",
    "cmake",
    "gcc",
    "g++",
    "cc",
    "clang",
    "javac",
    "python",  # can write files
    "perl",  # can write files
    "ruby",  # can write files
    # System Administration
    "useradd",
    "userdel",
    "usermod",
    "groupadd",
    "groupdel",
    "passwd",
    "mount",
    "umount",
    "mkfs",
    "fdisk",
    "parted",
    "swapon",
    "swapoff",
    # Database/Content Management
    "mysql",
    "psql",
    "sqlite3",
    "mongo",
    "redis-cli",
    # Version Control (can write)
    "git",
    "svn",
    "hg",
    "cvs",
    # Other Potentially Dangerous
    "patch",
    "cat",  # with redirection can overwrite
    "echo",  # with redirection can overwrite
    "printf",  # with redirection can overwrite
}


COMMAND_SPLIT = {";", "&&", "||", "|"}
CHANGE_DIRECTORY = {"cd"}


class DangerLevel(IntEnum):
    """The danger level of a command."""

    SAFE = 0  # Command is know to be generally save
    UNKNOWN = 1  # We don't know about this command
    DANGEROUS = 2  # Command is potentially dangerous (can modify filesystem)
    DESTRUCTIVE = 3  # Command is both dangerous and refers outside of project root


class CommandAtom(NamedTuple):
    """A command "atom"."""

    name: str
    """Name of the command."""
    level: DangerLevel
    """Danger level."""
    path: Path
    """The path to which this command is expected to apply."""


def analyze(project_dir: str, command_line: str) -> Iterable[CommandAtom]:
    """Analyze a command and generate information about potentially destructive commands.

    Args:
        project_dir: The project directory.
        command_line: A bash command line.

    Yields:
        `CommandAtom` objects.
    """
    project_path = Path(project_dir).resolve()

    import bashlex
    from bashlex import ast

    def recurse_nodes(root_path: Path, root_node: ast.node) -> Iterable[CommandAtom]:
        for node in root_node.parts:
            if node.kind != "command":
                continue
            command_name = node.parts[0].word
            parts = node.parts[1:]
            change_directory = command_name in CHANGE_DIRECTORY

            level = DangerLevel.UNKNOWN
            if command_name in SAFE_COMMANDS:
                level = DangerLevel.SAFE
            elif command_name in UNSAFE_COMMANDS:
                level = DangerLevel.DANGEROUS

            for command_node in parts:
                command_word = command_line[slice(*node.pos)]
                if command_node.kind == "command":
                    yield from recurse_nodes(root_path, command_node)
                elif not command_node.word.startswith(("-", "+")):
                    word = command_line[slice(*command_node.pos)]
                    if change_directory:
                        root_path = (root_path / word).resolve()
                    else:
                        target_path = root_path / word
                        if (
                            level == DangerLevel.DANGEROUS
                            and not target_path.is_relative_to(project_path)
                        ):
                            # If refers to a path outside of the project, upgrade to destructive
                            level = DangerLevel.DESTRUCTIVE

                        yield CommandAtom(command_word, level, target_path)

    for node in bashlex.parse(command_line):
        if node.kind == "list":
            yield from recurse_nodes(project_path, node)


if __name__ == "__main__":
    from rich import print

    for atom in analyze("./", "cd ../;rm foo"):
        print(atom)
